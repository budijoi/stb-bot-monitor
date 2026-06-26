import json
import os

CONFIG_FILE = "stb_list.json"

# Default config structure
DEFAULT_CONFIG = {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "allowed_users": [],
    "stb_list": []
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"[INFO] Config file '{CONFIG_FILE}' created. Please edit it.")
        return DEFAULT_CONFIG

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
