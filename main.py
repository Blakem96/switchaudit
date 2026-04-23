#!/usr/bin/env python3
"""Switch firmware update audit tool."""

import os
import sys

import click

from connect import open_connection, clear_credentials
from snapshot import save_snapshot, load_latest_snapshot, save_report
from report import build_report
from checks.boot import BootSourceCheck
from checks.vlans import VlanCheck
from checks.cdp import CdpCheck

# Ordered list of checks to run every phase
CHECKS = [BootSourceCheck(), VlanCheck(), CdpCheck()]


def _run_checks(conn) -> tuple[dict, dict]:
    """Run all checks and return (checks_summary, raw_snapshot_data)."""
    snapshot_data: dict = {}
    checks_summary: dict = {}

    for check in CHECKS:
        result = check.run(conn, snapshot_data)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name}: {result.detail.splitlines()[0]}")
        checks_summary[result.name] = {
            "passed": result.passed,
            "detail": result.detail,
        }

    return checks_summary, snapshot_data


@click.group()
def cli():
    """Switch firmware update audit tool."""


@cli.command()
@click.option("--switch", required=True, help="Switch IP address")
def pre(switch: str):
    """Connect to a switch and capture the pre-update snapshot."""
    conn = open_connection(switch)
    try:
        hostname = conn.find_prompt().strip("#").strip(">").strip()
        print(f"Connected to {hostname} ({switch})")
        print("Running pre-update checks...")
        checks_summary, snapshot_data = _run_checks(conn)
    finally:
        conn.disconnect()

    full_snapshot = {
        "hostname": hostname,
        "ip": switch,
        "checks": checks_summary,
        **snapshot_data,
    }
    save_snapshot(switch, hostname, "pre", full_snapshot)
    print("Pre-update snapshot complete.")


@cli.command()
@click.option("--switch", required=True, help="Switch IP address")
@click.option("--report", "gen_report", is_flag=True, default=False,
              help="Generate audit report immediately after post check")
def post(switch: str, gen_report: bool):
    """Connect to a switch and capture the post-update snapshot."""
    conn = open_connection(switch)
    try:
        hostname = conn.find_prompt().strip("#").strip(">").strip()
        print(f"Connected to {hostname} ({switch})")
        print("Running post-update checks...")
        checks_summary, snapshot_data = _run_checks(conn)
    finally:
        conn.disconnect()

    full_snapshot = {
        "hostname": hostname,
        "ip": switch,
        "checks": checks_summary,
        **snapshot_data,
    }
    post_path = save_snapshot(switch, hostname, "post", full_snapshot)
    print("Post-update snapshot complete.")

    if gen_report:
        _generate_report(switch, hostname, post_path)


@cli.command()
@click.option("--switch", required=True, help="Switch IP address")
def report(switch: str):
    """Generate a human-readable audit report from pre and post snapshots."""
    pre_data, pre_path = load_latest_snapshot(switch, "pre")
    post_data, post_path = load_latest_snapshot(switch, "post")
    hostname = post_data.get("hostname") or pre_data.get("hostname", "unknown")
    _generate_report(switch, hostname, post_path, pre_data, pre_path, post_data)


def _generate_report(switch, hostname, post_path, pre_data=None, pre_path=None, post_data=None):
    if pre_data is None:
        pre_data, pre_path = load_latest_snapshot(switch, "pre")
    if post_data is None:
        post_data, _ = load_latest_snapshot(switch, "post")

    content = build_report(switch, pre_data, post_data, pre_path, post_path)
    print()
    print(content)
    save_report(switch, hostname, content)


@cli.command("clear-creds")
def clear_creds():
    """Remove stored credentials from the OS keychain."""
    clear_credentials()


if __name__ == "__main__":
    # Ensure we run from the script's directory so config.yaml is found
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cli()
