"""Say whether the Watchtower server is between ETL cycles, and until when.

Usage, from the main checkout (the one with ``.env``)::

    uv run --with paramiko python .agents/skills/unraid-deploy/scripts/deploy_window.py

Every container start launches a full ETL cycle (about 47 minutes), and another
one starts two hours after each ends. A deploy swaps the container, which kills
a cycle in flight and starts a new one from scratch: deploy between cycles. This
reads the container's clock and the last scheduler marks in its log — nothing
else, and nothing is written — then prints whether a cycle is running, or the
window is open and when it closes. Exit 0 while the window has room for a
deploy, 1 otherwise.

The log's timestamps are the container's local time, so "now" is read from the
container too and the two are never compared with this machine's clock.
"""

import re
import shlex
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_deploy import ADDRESS, connect_quietly, deploy, run

CYCLE = timedelta(minutes=47)  # measured in production: 46-47 minutes
MARGIN = timedelta(minutes=15)  # a deploy takes a few minutes: do not start on the last of the window
DEFAULT_INTERVAL = timedelta(hours=2)
LOG = "/app/logs/scheduler.out.log"
INNER = f"date '+now %Y-%m-%d %H:%M:%S'; grep -E 'ETL Scheduler started' {LOG} | tail -n 1; grep -E 'Starting ETL execution|ETL Execution Finished' {LOG} | tail -n 2"
COMMAND = f"docker exec {deploy.DOCKER_IMAGE} sh -c {shlex.quote(INNER)}"
NOW = re.compile(r"^now (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$")
MARK = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)?\] (ETL Scheduler started|Starting ETL execution|ETL Execution Finished)(.*)$")
INTERVAL = re.compile(r" Interval: (\d+) s\.$")
START = "Starting ETL execution"
FINISH = "ETL Execution Finished"
Mark = tuple[datetime, str]


def read_log(text: str) -> tuple[datetime, list[Mark], timedelta]:
    """The container's clock, the cycle marks in the log's order, and the scheduler's interval."""
    now: datetime | None = None
    marks: list[Mark] = []
    interval = DEFAULT_INTERVAL
    for line in text.splitlines():
        line = line.strip()
        clock = NOW.match(line)
        if clock:
            now = datetime.strptime(clock[1], "%Y-%m-%d %H:%M:%S")
            continue
        mark = MARK.match(line)
        if not mark:
            continue
        when = datetime.strptime(mark[1], "%Y-%m-%d %H:%M:%S")
        seconds = INTERVAL.search(mark[3])
        if mark[2] == "ETL Scheduler started" and seconds:
            interval = timedelta(seconds=int(seconds[1]))
        else:
            marks.append((when, mark[2]))
    if now is None:
        raise ValueError("the container's clock did not come first")
    return now, marks, interval


def describe(now: datetime, marks: list[Mark], interval: timedelta) -> tuple[str, int]:
    """The answer for the last mark on the log: the window, or why there is none."""
    clock = f"Container time {now:%H:%M:%S}."
    if not marks:
        return f"{clock} The scheduler log has no cycle mark yet: a container that has just started runs its first cycle. Do not deploy now.", 1
    when, kind = marks[-1]
    if kind != FINISH:
        ends = when + CYCLE
        return (
            f"{clock} A cycle is running: it started at {when:%H:%M:%S} and takes about {CYCLE.seconds // 60} min, so it ends near {ends:%H:%M:%S}.\n"
            f"The deploy window then opens and closes at {ends + interval:%H:%M:%S}. Do not deploy now.",
            1,
        )
    closes = when + interval
    left = closes - now
    state = f"{clock} No cycle is running: the last one ended at {when:%H:%M:%S}."
    if left <= timedelta(0):
        return f"{state}\nThe deploy window closed at {closes:%H:%M:%S} and the next cycle is starting. Do not deploy now.", 1
    if left < MARGIN:
        return f"{state}\nThe deploy window closes at {closes:%H:%M:%S} and a deploy needs about {MARGIN.seconds // 60} min. Wait: the next window opens near {closes + CYCLE:%H:%M:%S}.", 1
    return f"{state}\nThe deploy window is open until {closes:%H:%M:%S} — {left.seconds // 60} minutes left.", 0


def main() -> int:
    """Read the server and say whether this is the moment to deploy."""
    try:
        ssh = connect_quietly(deploy.load_settings())
        try:
            _code, text = run(ssh, COMMAND)
        finally:
            ssh.close()
    except Exception as error:  # the message of a socket error can carry the host
        print(f"Could not read the server: {ADDRESS.sub('<ip>', str(error))}")
        return 1
    try:
        answer = describe(*read_log(text))
    except ValueError as error:
        print(f"Could not read the scheduler log: {error}")
        return 1
    print(answer[0])
    return answer[1]


if __name__ == "__main__":
    sys.exit(main())
