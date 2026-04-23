# Switch Update Audit Tool

A Python CLI tool for capturing pre- and post-update state on Cisco switches during manual firmware upgrades. Connects via SSH, runs a set of checks, saves timestamped JSON snapshots, and generates a human-readable audit report that flags any VLAN membership changes, lost CDP neighbors, or incorrect boot sources.

> **The tool assists and audits — it does not perform the firmware update itself.**

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Credentials](#credentials)
- [Usage](#usage)
  - [Pre-update snapshot](#1-pre-update-snapshot)
  - [Perform the update](#2-perform-the-update)
  - [Post-update snapshot](#3-post-update-snapshot)
  - [Generate the report](#4-generate-the-report)
  - [Combined post + report](#combined-post--report)
  - [Clear stored credentials](#clear-stored-credentials)
- [Audit Report](#audit-report)
- [Output Files](#output-files)
- [Checks Reference](#checks-reference)
  - [Boot Source](#boot-source-check)
  - [VLAN Membership](#vlan-membership-check)
  - [CDP Neighbors](#cdp-neighbors-check)
- [Adding New Checks](#adding-new-checks)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Requirements

- Python 3.10 or later
- SSH access to target Cisco switches (IOS / IOS-XE)
- Privilege level 15 (enable access) on the target switch

### Python dependencies

| Package | Purpose |
|---|---|
| `netmiko` | SSH connection + automatic pagination handling |
| `ntc-templates` / `textfsm` | Structured parsing of Cisco `show` output |
| `keyring` | OS-native credential storage |
| `pyyaml` | Config file parsing |
| `click` | CLI interface |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Blakem96/switchaudit.git
cd switchaudit

# (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Edit `config.yaml` before first use:

```yaml
switches: []
# Add switch IPs here, e.g.:
# switches:
#   - 10.0.0.1
#   - 10.0.0.2

vlan_watchlist:
  - GLOBAL
  - NIMS
  - WIRELESS
  - PRINT
  - BMS
  - AV

device_type: cisco_ios       # or cisco_ios_xe, cisco_nxos, etc.
keyring_service: switch-auditor
documents_dir: documents/switches
```

**`vlan_watchlist`** — VLAN names to monitor. The tool resolves names to IDs per-switch at runtime using `show vlan brief`, so the IDs can vary between switches.

**`device_type`** — Netmiko device type string. Common values:
- `cisco_ios` — IOS switches
- `cisco_ios_xe` — IOS-XE (Catalyst 9000 series etc.)
- `cisco_nxos` — NX-OS

The `switches` list is optional — you can always pass `--switch <ip>` directly on the command line.

---

## Credentials

Credentials are stored in the **OS native secret store**:
- **macOS** — Keychain
- **Windows** — Windows Credential Manager
- **Linux** — Secret Service / kwallet

On the **first run** the tool will prompt for a username and password and store them securely. All subsequent runs retrieve them silently — no credentials are ever written to disk or committed to the repository.

```
No stored credentials found. Please enter your switch credentials.
Username: jsmith
Password: ········
Credentials saved to OS keychain.
```

To update or remove stored credentials:

```bash
python main.py clear-creds
```

The next run will prompt again and store the new credentials.

---

## Usage

All commands are run from the `switchaudit` directory. Use `--switch` to target a specific switch IP.

### 1. Pre-update snapshot

Run this **before** any firmware changes. The tool connects to the switch, runs all checks, and saves a timestamped JSON snapshot.

```bash
python main.py pre --switch 10.0.0.1
```

Example output:

```
Connecting to 10.0.0.1...
Connected to CORE-SW-01 (10.0.0.1)
Running pre-update checks...
  [PASS] boot_source: Boot source confirmed as packages.conf
  [PASS] vlan_membership: GLOBAL: VLAN 10 (42 MACs)
  [PASS] cdp_neighbors: Captured 8 CDP neighbor(s)
Snapshot saved: documents/switches/10.0.0.1_CORE-SW-01/2024-11-15_09-30_pre.json
Pre-update snapshot complete.
```

### 2. Perform the update

Carry out the manual firmware update on the switch (image copy, `boot system` config changes, reload). The tool plays no part in this step.

### 3. Post-update snapshot

Run this **after** the switch has come back up and stabilised.

```bash
python main.py post --switch 10.0.0.1
```

### 4. Generate the report

```bash
python main.py report --switch 10.0.0.1
```

The report is printed to the terminal and saved as a `.txt` file in the `documents/` folder.

### Combined post + report

Use the `--report` flag on the `post` command to run both steps at once:

```bash
python main.py post --switch 10.0.0.1 --report
```

### Clear stored credentials

```bash
python main.py clear-creds
```

---

## Audit Report

A generated report looks like this:

```
======================================================================
SWITCH FIRMWARE UPDATE AUDIT REPORT
Generated : 2024-11-15 11:45
Switch IP : 10.0.0.1
Hostname  : CORE-SW-01
Pre snap  : 2024-11-15_09-30_pre.json
Post snap : 2024-11-15_11-44_post.json
======================================================================

CHECK RESULTS
----------------------------------------------------------------------
  boot_source               PRE: PASS  POST: PASS
    Post detail : Boot source confirmed as packages.conf
  vlan_membership           PRE: PASS  POST: PASS
    Post detail : GLOBAL: VLAN 10 (42 MACs)
                  NIMS: VLAN 20 (15 MACs)
                  WIRELESS: VLAN 30 (87 MACs)
  cdp_neighbors             PRE: PASS  POST: PASS
    Post detail : Captured 8 CDP neighbor(s)

VLAN MEMBERSHIP DIFF
----------------------------------------------------------------------
  No VLAN membership changes detected.

CDP NEIGHBOR DIFF
----------------------------------------------------------------------
  Unchanged neighbors : 8
  CDP neighbor list unchanged.

======================================================================
OVERALL RESULT: PASS
======================================================================
```

If a MAC address has moved to a different VLAN the diff table will highlight it:

```
VLAN MEMBERSHIP DIFF
----------------------------------------------------------------------
  MAC                  PRE VLAN     POST VLAN    FLAG
  ------------------ ---------- ---------- ------------
  aa:bb:cc:dd:ee:ff  STAFF        RESTRICTED   VLAN CHANGE
  11:22:33:44:55:66  IOT          (gone)       MISSING
```

A `VLAN CHANGE` or `MISSING` entry will cause the overall result to show **FAIL**.

---

## Output Files

All output lives under `documents/switches/` which is excluded from git via `.gitignore`.

```
documents/
└── switches/
    └── <ip>_<hostname>/
        ├── YYYY-MM-DD_HH-MM_pre.json      ← raw pre-update snapshot
        ├── YYYY-MM-DD_HH-MM_post.json     ← raw post-update snapshot
        └── YYYY-MM-DD_HH-MM_report.txt    ← human-readable audit report
```

- **JSON snapshots** — complete structured data from every check; useful for re-running the report without reconnecting.
- **Text report** — the audit artifact you keep or share with a change manager.

If you audit the same switch multiple times, `report` always diffs the **most recent** pre and post snapshots.

---

## Checks Reference

### Boot Source Check

**File:** `checks/boot.py`

Runs `show version` and verifies the switch is booting from `packages.conf`. A switch booting from a specific `.bin` image instead will fail this check.

| Result | Meaning |
|---|---|
| PASS | `packages.conf` found in boot variable or system image field |
| FAIL | Switch is booting from a different source (detail line shows the actual value) |

---

### VLAN Membership Check

**File:** `checks/vlans.py`

1. Runs `show vlan brief` and parses name → ID mappings.
2. Filters to only the VLANs listed in `vlan_watchlist` in `config.yaml`.
3. For each matched VLAN, runs `show mac address-table vlan <id>` and records every MAC address and its port.
4. Saves the result as `vlan_macs` in the snapshot JSON.

The report engine diffs `pre.vlan_macs` against `post.vlan_macs` and flags:
- **VLAN CHANGE** — MAC moved to a different named VLAN
- **MISSING** — MAC present pre-update, gone post-update
- **NEW** — MAC appeared post-update (informational, not a failure)

Snapshot format stored in JSON:
```json
{
  "GLOBAL":   { "aa:bb:cc:dd:ee:ff": "GigabitEthernet1/0/5" },
  "WIRELESS": { "11:22:33:44:55:66": "GigabitEthernet1/0/12" }
}
```

---

### CDP Neighbors Check

**File:** `checks/cdp.py`

Runs `show cdp neighbors` and captures the full neighbor table. Post-update, the diff engine compares device IDs and reports:
- **Unchanged** — neighbors present in both snapshots
- **NEW** — appeared post-update (informational)
- **REMOVED** — was present pre-update but is gone post-update (causes FAIL)

Snapshot format stored in JSON:
```json
[
  {
    "device_id": "ACCESS-SW-02",
    "local_intf": "Gi 1/1/1",
    "holdtime": "120",
    "capability": "S",
    "platform": "WS-C2960X",
    "port_id": "Gi0/1"
  }
]
```

---

## Adding New Checks

1. Create a new file in `checks/`, e.g. `checks/spanning_tree.py`.
2. Inherit from `BaseCheck` and implement `run()`:

```python
from .base import BaseCheck, CheckResult

class SpanningTreeCheck(BaseCheck):
    name = "spanning_tree"

    def run(self, conn, snapshot: dict) -> CheckResult:
        output = conn.send_command("show spanning-tree summary")
        snapshot["spanning_tree"] = output

        # your pass/fail logic here
        passed = "Root bridge for" in output
        return CheckResult(
            name=self.name,
            passed=passed,
            detail="Switch is root" if passed else "Switch is NOT root",
            data=output,
        )
```

3. Import and add it to the `CHECKS` list in `main.py`:

```python
from checks.spanning_tree import SpanningTreeCheck

CHECKS = [BootSourceCheck(), VlanCheck(), CdpCheck(), SpanningTreeCheck()]
```

The new check will automatically appear in snapshots and reports.

---

## Project Structure

```
switchaudit/
├── main.py              # CLI entrypoint (pre / post / report / clear-creds)
├── config.yaml          # Switch list, VLAN watchlist, device type
├── connect.py           # Keyring credential storage + Netmiko connection handler
├── snapshot.py          # Save and load timestamped JSON snapshots
├── report.py            # Diff engine and human-readable report builder
├── requirements.txt
├── .gitignore           # Excludes documents/ from version control
└── checks/
    ├── base.py          # BaseCheck class and CheckResult dataclass
    ├── boot.py          # Boot source check (packages.conf)
    ├── vlans.py         # VLAN membership snapshot and diff
    └── cdp.py           # CDP neighbor snapshot and diff
```

`documents/` is created automatically on first run and is excluded from git — it is your local audit trail only.

---

## Troubleshooting

**Authentication failure on connect**

Stored credentials may be incorrect. Clear them and re-enter:
```bash
python main.py clear-creds
python main.py pre --switch 10.0.0.1
```

**`No pre snapshot found for <ip>`**

The pre command has not been run yet for this switch, or the `documents/` folder was moved. Run `pre` first.

**VLAN not appearing in snapshot**

Check that the VLAN name in `config.yaml` matches exactly (case-insensitive) what appears in `show vlan brief` output on the switch.

**`keyring` errors on Linux**

A secret store backend must be running. Install and start one:
```bash
# Debian / Ubuntu
sudo apt install gnome-keyring
# or
sudo apt install python3-secretstorage
```

Alternatively, install the `keyrings.alt` package for a file-backed fallback (less secure):
```bash
pip install keyrings.alt
```

**Netmiko timeout on large MAC tables**

Increase the read timeout by setting `global_delay_factor` in `connect.py` if you see truncated output on switches with very large MAC address tables.
