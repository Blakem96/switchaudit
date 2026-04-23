from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    data: Any = None  # raw captured data for snapshot storage


class BaseCheck:
    name: str = "unnamed"

    def run(self, conn, snapshot: dict) -> CheckResult:
        """Execute the check against an open Netmiko connection.

        Populate snapshot with any data that should be diffed post-reboot.
        Returns a CheckResult with pass/fail and human-readable detail.
        """
        raise NotImplementedError
