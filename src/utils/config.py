
import os
import json

DEFAULT_CONFIG = {
    "style": "conventional",
    "max_title_length": 72,
    "include_body": True,
    "custom_instructions": "",
    "auto_commit": False
}


def load_config(path="config.json"):
    if not os.path.exists(path):
        return DEFAULT_CONFIG

    try:
        with open(path, "r") as f:
            user_config = json.load(f)
    except Exception:
        return DEFAULT_CONFIG

    # Merge user config over defaults
    return {**DEFAULT_CONFIG, **user_config}