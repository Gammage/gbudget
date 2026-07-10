import json
import os
import sys

if sys.platform == "win32":
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "gbudget")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/gbudget")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "vault_path": "",
    "statement_day": 1,
    "last_statement_month": "",
    "statements_enabled": False
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def init_config():
    config = DEFAULT_CONFIG.copy()
    save_config(config)
    return config
