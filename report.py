from datetime import datetime
from pathlib import Path


def _hr(char: str = "-", width: int = 70) -> str:
    return char * width


def diff_vlan_macs(pre_macs: dict, post_macs: dict) -> list[dict]:
    """Return list of MACs that changed VLAN between pre and post snapshots."""
    changes = []
    all_vlans = set(pre_macs) | set(post_macs)

    # Build mac→vlan maps
    pre_mac_vlan: dict[str, str] = {}
    post_mac_vlan: dict[str, str] = {}
    for vlan, macs in pre_macs.items():
        for mac in macs:
            pre_mac_vlan[mac] = vlan
    for vlan, macs in post_macs.items():
        for mac in macs:
            post_mac_vlan[mac] = vlan

    for mac, pre_vlan in pre_mac_vlan.items():
        post_vlan = post_mac_vlan.get(mac)
        if post_vlan is None:
            changes.append({"mac": mac, "pre": pre_vlan, "post": "(gone)", "flag": "MISSING"})
        elif post_vlan != pre_vlan:
            flag = "VLAN CHANGE"
            changes.append({"mac": mac, "pre": pre_vlan, "post": post_vlan, "flag": flag})

    for mac, post_vlan in post_mac_vlan.items():
        if mac not in pre_mac_vlan:
            changes.append({"mac": mac, "pre": "(new)", "post": post_vlan, "flag": "NEW"})

    return changes


def diff_cdp(pre_neighbors: list, post_neighbors: list) -> dict:
    pre_ids = {n["device_id"] for n in pre_neighbors}
    post_ids = {n["device_id"] for n in post_neighbors}
    return {
        "added": sorted(post_ids - pre_ids),
        "removed": sorted(pre_ids - post_ids),
        "unchanged_count": len(pre_ids & post_ids),
    }


def build_report(
    ip: str,
    pre: dict,
    post: dict,
    pre_path: Path,
    post_path: Path,
) -> str:
    lines = []
    a = lines.append

    hostname = pre.get("hostname", "unknown")
    a(_hr("="))
    a(f"SWITCH FIRMWARE UPDATE AUDIT REPORT")
    a(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    a(f"Switch IP : {ip}")
    a(f"Hostname  : {hostname}")
    a(f"Pre snap  : {pre_path.name}")
    a(f"Post snap : {post_path.name}")
    a(_hr("="))

    # --- Per-check results ---
    a("")
    a("CHECK RESULTS")
    a(_hr())

    pre_checks = pre.get("checks", {})
    post_checks = post.get("checks", {})
    all_check_names = list(dict.fromkeys(list(pre_checks) + list(post_checks)))

    overall_pass = True
    for check_name in all_check_names:
        pre_r = pre_checks.get(check_name, {})
        post_r = post_checks.get(check_name, {})
        pre_status = "PASS" if pre_r.get("passed") else "FAIL"
        post_status = "PASS" if post_r.get("passed") else "FAIL"
        if not post_r.get("passed", True):
            overall_pass = False
        a(f"  {check_name:<25} PRE: {pre_status:<4}  POST: {post_status}")
        if pre_r.get("detail"):
            a(f"    Pre  detail : {pre_r['detail']}")
        if post_r.get("detail"):
            a(f"    Post detail : {post_r['detail']}")

    # --- VLAN diff ---
    a("")
    a("VLAN MEMBERSHIP DIFF")
    a(_hr())
    pre_macs = pre.get("vlan_macs", {})
    post_macs = post.get("vlan_macs", {})
    if pre_macs and post_macs:
        changes = diff_vlan_macs(pre_macs, post_macs)
        if changes:
            overall_pass = False
            a(f"  {'MAC':<20} {'PRE VLAN':<12} {'POST VLAN':<12} FLAG")
            a(f"  {'-'*18} {'-'*10} {'-'*10} {'-'*12}")
            for c in changes:
                a(f"  {c['mac']:<20} {c['pre']:<12} {c['post']:<12} {c['flag']}")
        else:
            a("  No VLAN membership changes detected.")
    else:
        a("  VLAN snapshot data unavailable.")

    # --- CDP diff ---
    a("")
    a("CDP NEIGHBOR DIFF")
    a(_hr())
    pre_cdp = pre.get("cdp_neighbors", [])
    post_cdp = post.get("cdp_neighbors", [])
    if pre_cdp is not None and post_cdp is not None:
        cdp_diff = diff_cdp(pre_cdp, post_cdp)
        a(f"  Unchanged neighbors : {cdp_diff['unchanged_count']}")
        if cdp_diff["added"]:
            a(f"  NEW neighbors       : {', '.join(cdp_diff['added'])}")
        if cdp_diff["removed"]:
            overall_pass = False
            a(f"  REMOVED neighbors   : {', '.join(cdp_diff['removed'])}")
        if not cdp_diff["added"] and not cdp_diff["removed"]:
            a("  CDP neighbor list unchanged.")
    else:
        a("  CDP data unavailable.")

    # --- Summary ---
    a("")
    a(_hr("="))
    result = "PASS" if overall_pass else "FAIL"
    a(f"OVERALL RESULT: {result}")
    a(_hr("="))
    a("")

    return "\n".join(lines)
