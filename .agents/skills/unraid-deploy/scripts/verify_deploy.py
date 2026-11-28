"""Compare the files inside the running Watchtower container with a commit, by md5.

Usage, from the main checkout (the one with ``.env``)::

    uv run --with paramiko python .agents/skills/unraid-deploy/scripts/verify_deploy.py --since <commit production ran before>
    uv run --with paramiko python .agents/skills/unraid-deploy/scripts/verify_deploy.py --since <commit> --expect <commit>
    uv run --with paramiko python .agents/skills/unraid-deploy/scripts/verify_deploy.py --all --expect <commit>

``--since`` names the commit production ran before the deploy; the files that changed up to ``--expect`` (default ``HEAD``) are compared, ``--all`` compares every shipped file. Only what the deploy ships is looked at (``INCLUDE_PATHS`` in ``deployment/deploy.py``), against the committed bytes: the archive is normalized to LF, so the commit is what the server should hold whatever the checkout's line endings are. A file the commit no longer holds was deleted before it: it matches when the container does not hold it either, and is ``STILL IN CONTAINER`` when the image kept it.

The server side is one read-only ``md5sum`` per batch of files, inside the container. Nothing is written anywhere, and the host is never printed: the connection is opened without the line ``deploy.py`` echoes.
"""

import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path.cwd()))

from deployment import deploy

BATCH = 200
MD5_LINE = re.compile(r"^([0-9a-f]{32}) [ *](.+)$")
# What md5sum answers for a file that is not there; the path comes bare or between quotes, by the coreutils build.
MISSING = re.compile(r"^md5sum: ['\"]?(.+?)['\"]?: No such file or directory$")
ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def shipped(path: str) -> bool:
    """Whether the deploy archive carries ``path``: under an entry of ``INCLUDE_PATHS`` and not dropped by the filter."""
    if set(path.split("/")) & deploy.EXCLUDED_DIR_NAMES or path.endswith(deploy.EXCLUDED_SUFFIXES):
        return False
    return any(path == top or path.startswith(top + "/") for top in deploy.INCLUDE_PATHS)


def git(*arguments: str) -> bytes:
    """Run a git command in the checkout and return its stdout."""
    return subprocess.run(["git", *arguments], capture_output=True, check=True).stdout


def shipped_paths(since: str, expect: str, everything: bool) -> list[str]:
    """The shipped paths to compare: every tracked one, or the ones that changed between two commits."""
    if everything:
        names = git("ls-files", "-z").decode("utf-8").split("\0")
    else:
        names = git("diff", "--name-only", "-z", since, expect).decode("utf-8").split("\0")
    return sorted(name for name in names if name and shipped(name))


def committed_md5(commit: str, paths: list[str]) -> dict[str, str]:
    """md5 of each path's content at ``commit``; a path the commit does not hold is left out."""
    request = "".join(f"{commit}:{path}\n" for path in paths).encode("utf-8")
    answer = subprocess.run(["git", "cat-file", "--batch"], input=request, capture_output=True, check=True).stdout
    hashes: dict[str, str] = {}
    position = 0
    for path in paths:
        end_of_header = answer.index(b"\n", position)
        header = answer[position:end_of_header].split()
        if header[-1] == b"missing":
            position = end_of_header + 1
            continue
        size = int(header[2])
        hashes[path] = hashlib.md5(answer[end_of_header + 1 : end_of_header + 1 + size]).hexdigest()
        position = end_of_header + 1 + size + 1
    return hashes


def connect_quietly(settings: deploy.DeploySettings) -> Any:
    """Open the SSH session as ``deploy.connect`` does, without printing the host."""
    import paramiko  # deploy-time dependency: uv run --with paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict[str, Any] = {"username": settings.username, "timeout": 30}
    if settings.password:
        connect_kwargs["password"] = settings.password
    else:
        connect_kwargs["key_filename"] = os.path.expanduser("~/.ssh/id_ed25519")
    ssh.connect(settings.server_ip, **connect_kwargs)
    return ssh


def run(ssh: Any, command: str) -> tuple[int, str]:
    """Run ``command`` on the server and return its exit status with the whole output, stdout and stderr together."""
    channel = ssh.get_transport().open_session()
    channel.set_combine_stderr(True)
    channel.exec_command(command)
    with channel.makefile("rb") as output:
        text = output.read().decode(errors="replace")
    return channel.recv_exit_status(), text


def container_md5(ssh: Any, paths: list[str]) -> tuple[dict[str, str], list[str]]:
    """md5 of each path inside the container, and the output lines that were not a digest (an error message)."""
    digests: dict[str, str] = {}
    unparsed: list[str] = []
    for start in range(0, len(paths), BATCH):
        inner = "cd /app && md5sum -- " + " ".join(shlex.quote(path) for path in paths[start : start + BATCH])
        _code, text = run(ssh, f"docker exec {deploy.DOCKER_IMAGE} sh -c {shlex.quote(inner)}")
        for line in text.splitlines():
            match = MD5_LINE.match(line.strip())
            if match:
                digests[match[2].strip()] = match[1]
            elif line.strip():
                unparsed.append(line.strip())
    return digests, unparsed


def judge(paths: list[str], expected: dict[str, str], actual: dict[str, str], unexplained: list[str]) -> tuple[list[str], int, int]:
    """The report of one comparison: its lines, how many files do not match, and how many deleted ones are gone.

    ``expected`` holds the md5 of each path as the commit has it, so a path left out was deleted before the commit: it
    matches when the container does not hold it either. ``unexplained`` holds what ``md5sum`` wrote that was not a digest.
    Its line for a file that is not there goes with the verdict of that file, which already says whether its absence is
    right; any other line counts against the result.
    """
    lines: list[str] = []
    failed = gone = 0
    for path in paths:
        if path not in expected and path not in actual:
            gone += 1
            lines.append(f"deleted    {path}")
            continue
        if path not in expected:
            verdict = "STILL IN CONTAINER"
        elif path not in actual:
            verdict = "NOT IN CONTAINER"
        elif actual[path] != expected[path]:
            verdict = "DIFFERENT"
        else:
            lines.append(f"ok         {path}")
            continue
        failed += 1
        lines.append(f"{verdict:<17}  {path}  (commit {expected.get(path, '-')}, container {actual.get(path, '-')})")
    asked = set(paths)
    for line in unexplained:
        missing = MISSING.match(line)
        if missing and missing[1] in asked:
            if missing[1] in expected:
                lines.append(f"server said: {line}")
            continue
        lines.append(f"server said: {line}")
        failed += 1
    return lines, failed, gone


def main() -> int:
    """Compare the container with the commit; exit 1 on any difference."""
    # "server said" lines carry whatever the server wrote, and a pipe on Windows encodes it with the code page of the
    # machine: write UTF-8 whatever the locale is, and never stop on a character.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", help="commit production ran before this deploy (required unless --all)")
    parser.add_argument("--expect", default="HEAD", help="the commit the container should hold (default HEAD)")
    parser.add_argument("--all", action="store_true", help="compare every shipped file, not only the changed ones")
    options = parser.parse_args()
    if not options.all and not options.since:
        parser.error("--since is needed unless --all compares every shipped file")

    paths = shipped_paths(options.since, options.expect, options.all)
    if not paths:
        print("No shipped file changed between those commits.")
        return 0
    expected = committed_md5(options.expect, paths)

    try:
        ssh = connect_quietly(deploy.load_settings())
        try:
            actual, unexplained = container_md5(ssh, paths)
        finally:
            ssh.close()
    except Exception as error:  # the message of a socket error can carry the host
        print(f"Could not read the container: {ADDRESS.sub('<ip>', str(error))}")
        return 1

    lines, failed, gone = judge(paths, expected, actual, unexplained)
    for line in lines:
        print(ADDRESS.sub("<ip>", line))
    deleted = f" ({gone} deleted before it, and gone from the container)" if gone else ""
    print(f"\n{len(paths) - failed} of {len(paths)} shipped file(s) match {options.expect[:12]}{deleted}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
