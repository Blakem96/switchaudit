import re
from .base import BaseCheck, CheckResult


class BootSourceCheck(BaseCheck):
    name = "boot_source"

    def run(self, conn, snapshot: dict) -> CheckResult:
        output = conn.send_command("show version")
        snapshot["show_version"] = output

        # IOS-XE: "BOOT variable = flash:packages.conf"
        # IOS:    "System image file is "flash:packages.conf""
        boot_ok = bool(re.search(r"packages\.conf", output, re.IGNORECASE))

        if boot_ok:
            return CheckResult(
                name=self.name,
                passed=True,
                detail="Boot source confirmed as packages.conf",
                data=output,
            )
        else:
            # Try to extract what it is booting from for the detail line
            match = re.search(r"BOOT variable\s*=\s*(.+)", output)
            if not match:
                match = re.search(r'System image file is "(.+)"', output)
            boot_val = match.group(1).strip() if match else "unknown"
            return CheckResult(
                name=self.name,
                passed=False,
                detail=f"Boot source is NOT packages.conf — found: {boot_val}",
                data=output,
            )
