
import os
import json
from gitai.utils.log import setup_logger

logger = setup_logger(__name__, "app.log")

DEFAULT_CONFIG = {
    "style": "conventional",
    "max_title_length": 72,
    "include_body": True,
    "custom_instructions": "",
    "auto_commit": False
}


def load_config(path="config.json"):
    if not os.path.exists(path):
        logger.debug(f"Config file '{path}' not found, using default values")
        return DEFAULT_CONFIG

    try:
        with open(path, "r") as f:
            user_config = json.load(f)
        logger.debug(f"Loaded user config from '{path}'")
    except Exception as e:
        logger.warning(f"Failed to parse config file '{path}', using defaults: {e}")
        return DEFAULT_CONFIG

    # Merge user config over defaults
    config = {**DEFAULT_CONFIG, **user_config}
    logger.debug(f"Merged config: {config}")
    return config
