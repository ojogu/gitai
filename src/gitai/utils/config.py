import os
import json
from gitai.utils.log import setup_logger, sanitize_for_logging
from gitai.utils.exceptions import ConfigurationError, FileNotFoundError as GitAIFileNotFoundError

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
    """
    Load configuration from a JSON file, falling back to defaults.
    
    Args:
        path: Path to the config file (relative or absolute)
        
    Returns:
        dict: Merged configuration with defaults
        
    Raises:
        ConfigurationError: If config file exists but cannot be parsed
    """
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
        
        # Validate that it's a dictionary
        if not isinstance(user_config, dict):
            raise ConfigurationError(
                f"Config file '{path}' must contain a JSON object, got {type(user_config).__name__}",
                details={"path": path, "type": type(user_config).__name__}
            )
            
    except json.JSONDecodeError as e:
        raise ConfigurationError(
            f"Failed to parse config file '{path}': Invalid JSON",
            details={"path": path, "error": str(e)},
            suggestion="Check that the config file contains valid JSON."
        )
    except PermissionError as e:
        raise ConfigurationError(
            f"Permission denied reading config file '{path}'",
            details={"path": path},
            suggestion="Check file permissions."
        )
    except Exception as e:
        raise ConfigurationError(
            f"Unexpected error reading config file '{path}': {str(e)}",
            details={"path": path, "error_type": type(e).__name__}
        )

    # Merge user config over defaults
    config = {**DEFAULT_CONFIG, **user_config}
    logger.debug(f"Merged config: {sanitize_for_logging(config)}")
    return config

