import getpass
import keyring
import yaml
from netmiko import ConnectHandler

_CONFIG_PATH = "config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_credentials() -> tuple[str, str]:
    cfg = _load_config()
    service = cfg.get("keyring_service", "switch-auditor")
    username = keyring.get_password(service, "username")
    password = keyring.get_password(service, "password") if username else None

    if not username or not password:
        print("No stored credentials found. Please enter your switch credentials.")
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        keyring.set_password(service, "username", username)
        keyring.set_password(service, "password", password)
        print("Credentials saved to OS keychain.")

    return username, password


def clear_credentials() -> None:
    cfg = _load_config()
    service = cfg.get("keyring_service", "switch-auditor")
    keyring.delete_password(service, "username")
    keyring.delete_password(service, "password")
    print("Credentials cleared from OS keychain.")


def open_connection(host: str) -> ConnectHandler:
    cfg = _load_config()
    username, password = get_credentials()
    device = {
        "device_type": cfg.get("device_type", "cisco_ios"),
        "host": host,
        "username": username,
        "password": password,
    }
    print(f"Connecting to {host}...")
    conn = ConnectHandler(**device)
    conn.enable()
    return conn
