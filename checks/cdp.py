import re
from .base import BaseCheck, CheckResult


def _parse_cdp_neighbors(output: str) -> list[dict]:
    """Parse 'show cdp neighbors' into a list of neighbor dicts."""
    neighbors = []
    # Skip header lines; data lines have device-id + local-intf + holdtime + capability + platform + port-id
    in_table = False
    for line in output.splitlines():
        if re.match(r"^Device ID", line, re.IGNORECASE):
            in_table = True
            continue
        if not in_table:
            continue
        # Skip blank / separator lines
        if not line.strip() or line.startswith("-"):
            continue
        # CDP output can wrap; a full entry has at least 5 tokens
        parts = line.split()
        if len(parts) >= 5:
            neighbors.append({
                "device_id": parts[0],
                "local_intf": f"{parts[1]} {parts[2]}",
                "holdtime": parts[3],
                "capability": parts[4],
                "platform": parts[5] if len(parts) > 5 else "",
                "port_id": parts[-1],
            })
    return neighbors


class CdpCheck(BaseCheck):
    name = "cdp_neighbors"

    def run(self, conn, snapshot: dict) -> CheckResult:
        output = conn.send_command("show cdp neighbors")
        neighbors = _parse_cdp_neighbors(output)
        snapshot["cdp_neighbors"] = neighbors
        snapshot["cdp_raw"] = output

        return CheckResult(
            name=self.name,
            passed=True,
            detail=f"Captured {len(neighbors)} CDP neighbor(s)",
            data=neighbors,
        )
