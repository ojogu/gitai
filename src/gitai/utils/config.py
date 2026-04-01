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


def _get_project_root() -> str:
    """Find the project root by looking for pyproject.toml."""
    current = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return current


def load_config(path="config.json"):
    # If path is absolute or doesn't exist, try relative to project root
    if not os.path.isabs(path) and not os.path.exists(path):
        root_config = os.path.join(_get_project_root(), path)
        if os.path.exists(root_config):
            path = root_config

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

