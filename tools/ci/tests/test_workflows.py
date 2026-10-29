"""Checks of the GitHub workflows that need no runner."""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[3] / ".github" / "workflows"
DEVICE_NODE = re.compile(r"/dev/disk\d")


def test_no_step_names_a_runner_disk_device():
    """Device names change between runner images (/dev/disk3s1s1 is gone on macos-15); name a path instead."""
    found = [
        f"{workflow.name}:{number}"
        for workflow in sorted(WORKFLOWS.glob("*.yml"))
        for number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1)
        if DEVICE_NODE.search(line)
    ]
    assert not found, found
