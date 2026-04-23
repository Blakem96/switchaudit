import re
import yaml
from .base import BaseCheck, CheckResult


def _load_watchlist() -> list[str]:
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    return [v.upper() for v in cfg.get("vlan_watchlist", [])]


def _parse_vlan_brief(output: str) -> dict[str, str]:
    """Return {vlan_name_upper: vlan_id} from 'show vlan brief' output."""
    mapping = {}
    for line in output.splitlines():
        # e.g. "10   STAFF                            active    Gi1/0/1, Gi1/0/2"
        match = re.match(r"^\s*(\d+)\s+(\S+)\s+active", line)
        if match:
            vlan_id, vlan_name = match.group(1), match.group(2)
            mapping[vlan_name.upper()] = vlan_id
    return mapping


def _parse_mac_table(output: str) -> dict[str, str]:
    """Return {mac_address: interface} from 'show mac address-table vlan X'."""
    macs = {}
    for line in output.splitlines():
        # e.g. "  10    aabb.ccdd.eeff    DYNAMIC     Gi1/0/5"
        match = re.match(
            r"^\s*\d+\s+([\da-f]{4}\.[\da-f]{4}\.[\da-f]{4})\s+\w+\s+(\S+)",
            line,
            re.IGNORECASE,
        )
        if match:
            raw_mac = match.group(1)
            # normalise cisco dotted-hex to colon-separated
            mac = ":".join(
                raw_mac.replace(".", "")[i : i + 2]
                for i in range(0, 12, 2)
            )
            macs[mac.lower()] = match.group(2)
    return macs


class VlanCheck(BaseCheck):
    name = "vlan_membership"

    def run(self, conn, snapshot: dict) -> CheckResult:
        watchlist = _load_watchlist()

        vlan_output = conn.send_command("show vlan brief")
        vlan_map = _parse_vlan_brief(vlan_output)
        snapshot["vlan_map"] = vlan_map

        matched = {name: vid for name, vid in vlan_map.items() if name in watchlist}
        not_found = [n for n in watchlist if n not in vlan_map]

        mac_snapshot: dict[str, dict[str, str]] = {}
        for vlan_name, vlan_id in matched.items():
            mac_output = conn.send_command(f"show mac address-table vlan {vlan_id}")
            mac_snapshot[vlan_name] = _parse_mac_table(mac_output)

        snapshot["vlan_macs"] = mac_snapshot

        detail_lines = [f"{name}: VLAN {vid} ({len(mac_snapshot.get(name, {}))} MACs)" for name, vid in matched.items()]
        if not_found:
            detail_lines.append(f"VLANs not found on switch: {', '.join(not_found)}")

        return CheckResult(
            name=self.name,
            passed=True,
            detail="\n  ".join(detail_lines) if detail_lines else "No watched VLANs found",
            data=mac_snapshot,
        )
