"""Hermetic tests for the archive line-ending normalization (T-118).

With ``core.autocrlf=true`` the Windows working tree holds CRLF copies of every
text file; ``deploy.normalize_for_archive`` collapses them back to LF on the way
into the tar (and leaves binary files byte-identical). Temp trees only: no
docker, no ssh, no network.
"""

import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# `deployment/` is a plain directory at the repo root, not an installed package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from deployment import deploy

# ---------------------------------------------------------------------------
# normalize_for_archive: the pure helper
# ---------------------------------------------------------------------------


def test_lf_content_passes_through_unchanged():
    text = b"a = 1\nb = 2\n"
    assert deploy.normalize_for_archive(text) == text


def test_crlf_is_normalized_to_lf():
    assert deploy.normalize_for_archive(b"a = 1\r\nb = 2\r\n") == b"a = 1\nb = 2\n"


def test_mixed_endings_normalize_only_the_crlf_pairs():
    """CRLF collapses, LF stays, a lone CR (old Mac) is not touched."""
    assert deploy.normalize_for_archive(b"one\r\ntwo\nthree\r") == b"one\ntwo\nthree\r"


def test_binary_data_with_a_nul_byte_is_untouched():
    """The NUL byte (git's binary heuristic) turns off the rewrite: the CRs stay."""
    data = b"\x89PNG\r\n\x1a\n\x00\x00\r\ntrailer"
    assert deploy.normalize_for_archive(data) == data


def test_empty_input_stays_empty():
    assert deploy.normalize_for_archive(b"") == b""


# ---------------------------------------------------------------------------
# create_archive: the bytes that actually land in the tar
# ---------------------------------------------------------------------------


def _extract(archive: Path, member: str) -> bytes:
    with tarfile.open(archive) as tar:
        payload = tar.extractfile(member)
        assert payload is not None, member  # directories carry no payload
        return payload.read()


def test_archive_stores_text_as_lf_and_binary_verbatim(tmp_path: Path):
    """One CRLF text file is stored normalized; a binary file keeps its exact bytes."""
    root = tmp_path / "tree"
    (root / "src").mkdir(parents=True)
    (root / "src" / "crlf.txt").write_bytes(b"alpha\r\nbeta\r\n")
    (root / "src" / "blob.bin").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\r\ntrailer")

    archive = tmp_path / "out.tar.gz"
    deploy.create_archive(str(archive), root=str(root), include_paths=["src"])

    assert _extract(archive, "src/crlf.txt") == b"alpha\nbeta\n"
    assert _extract(archive, "src/blob.bin") == b"\x89PNG\r\n\x1a\n\x00\x00\r\ntrailer"


def test_symlinks_keep_their_linkname(tmp_path: Path):
    """Non-regular files are metadata-only members, exactly as ``tar.add`` built them."""
    root = tmp_path / "tree"
    (root / "src").mkdir(parents=True)
    (root / "src" / "real.txt").write_bytes(b"real\n")
    link = root / "src" / "link.txt"
    try:
        link.symlink_to("real.txt")
    except OSError:  # unprivileged Windows cannot create symlinks
        pytest.skip("symlinks are not creatable in this environment")

    archive = tmp_path / "out.tar.gz"
    deploy.create_archive(str(archive), root=str(root), include_paths=["src"])

    with tarfile.open(archive) as tar:
        member = tar.getmember("src/link.txt")
    assert member.issym()
    assert member.linkname == "real.txt"
