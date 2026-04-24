import json
from datetime import datetime
from pathlib import Path

import yaml


def _load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def _switch_dir(ip: str, hostname: str) -> Path:
    cfg = _load_config()
    base = Path(cfg.get("documents_dir", "documents/switches"))
    folder = base / f"{ip}_{hostname}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_snapshot(ip: str, hostname: str, phase: str, data: dict) -> Path:
    folder = _switch_dir(ip, hostname)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = folder / f"{ts}_{phase}.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Snapshot saved: {filename}")
    return filename


def load_latest_snapshot(ip: str, phase: str) -> tuple[dict, Path]:
    cfg = _load_config()
    base = Path(cfg.get("documents_dir", "documents/switches"))
    candidates = []
    for folder in base.glob(f"{ip}_*"):
        candidates.extend(folder.glob(f"*_{phase}.json"))
    if not candidates:
        raise FileNotFoundError(f"No {phase} snapshot found for {ip}")
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    with open(latest) as f:
        return json.load(f), latest


def save_running_config(ip: str, hostname: str, phase: str, config: str) -> Path:
    folder = _switch_dir(ip, hostname)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = folder / f"{ts}_{phase}_running-config.txt"
    with open(filename, "w") as f:
        f.write(config)
    print(f"Running config saved: {filename}")
    return filename


def load_latest_running_config(ip: str, phase: str) -> tuple[str, Path] | None:
    cfg = _load_config()
    base = Path(cfg.get("documents_dir", "documents/switches"))
    candidates = []
    for folder in base.glob(f"{ip}_*"):
        candidates.extend(folder.glob(f"*_{phase}_running-config.txt"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.read_text(), latest


def save_report(ip: str, hostname: str, content: str) -> Path:
    folder = _switch_dir(ip, hostname)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = folder / f"{ts}_report.txt"
    with open(filename, "w") as f:
        f.write(content)
    print(f"Report saved: {filename}")
    return filename
