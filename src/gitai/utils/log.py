# log_util.py
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
from rich.logging import RichHandler  # Rich handler for colored console output

# Determine the root directory of the project.
# This script is in: src/gitai/utils/log.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")

# Patterns to detect sensitive information
SENSITIVE_PATTERNS = [
    # API Keys and Tokens (various formats)
    r'(api[_-]?key|apikey|api[_-]?secret|secret[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
    r'(api[_-]?key|apikey|api[_-]?secret|secret[_-]?key)\s+(is|was|are|were|has|have|had|be|been|being|will|shall|can|could|may|might|must|should|would)\s+([a-zA-Z0-9_\-]{10,})',
    r'(token|auth[_-]?token|access[_-]?token|bearer)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
    r'(token|auth[_-]?token|access[_-]?token)\s+(is|was|are|were|has|have|had|be|been|being|will|shall|can|could|may|might|must|should|would)\s+([a-zA-Z0-9_\-\.]{10,})',
    
    # Passwords (various formats)
    r'(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})["\']?',
    r'(password|passwd|pwd)\s+(is|was|are|were|has|have|had|be|been|being|will|shall|can|could|may|might|must|should|would)\s+(\S{8,})',
    
    # Email addresses
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    
    # Private keys
    r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
    r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
    
    # Credit cards (basic pattern)
    r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    
    # Social Security Numbers
    r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
    
    # IP addresses (could be sensitive in some contexts)
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    
    # Common API key prefixes (Stripe, AWS, etc.)
    r'\b(sk_live_[a-zA-Z0-9]+|sk_test_[a-zA-Z0-9]+|AKIA[a-zA-Z0-9]{16}|ghp_[a-zA-Z0-9]{36})\b',
]

# Keywords that indicate sensitive data
SENSITIVE_KEYWORDS = [
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'api_secret', 'access_token', 'auth_token', 'private_key', 'credential'
]


def _sanitize_string(value: str, max_length: int = 100) -> str:
    """
    Sanitize a string by removing or masking sensitive information.
    
    Args:
        value: The string to sanitize
        max_length: Maximum length to return (prevents logging huge data)
        
    Returns:
        Sanitized string with sensitive data masked
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length] + f"... [truncated, {len(value)} chars total]"
    
    # Apply sensitive patterns
    for pattern in SENSITIVE_PATTERNS:
        # Replace sensitive matches with [REDACTED]
        value = re.sub(pattern, '[REDACTED]', value, flags=re.IGNORECASE)
    
    return value


def _sanitize_dict(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sanitize a dictionary by removing or masking sensitive values.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: Additional keys to always redact
        
    Returns:
        Sanitized dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = []
    
    # Add default sensitive keys
    sensitive_keys.extend(SENSITIVE_KEYWORDS)
    sensitive_keys = list(set(sensitive_keys))  # Remove duplicates
    
    sanitized = {}
    for key, value in data.items():
        # Check if key indicates sensitive data
        if any(keyword in key.lower() for keyword in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value, sensitive_keys)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_string(str(v)) for v in value]
        elif isinstance(value, str):
            sanitized[key] = _sanitize_string(value)
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_for_logging(data: Any, sensitive_keys: Optional[List[str]] = None) -> Any:
    """
    Main sanitization function that handles various data types.
    
    Args:
        data: Any data to sanitize (string, dict, list, or other)
        sensitive_keys: Additional keys to always redact
        
    Returns:
        Sanitized data suitable for logging
    """
    if data is None:
        return None
    
    if isinstance(data, dict):
        return _sanitize_dict(data, sensitive_keys)
    elif isinstance(data, list):
        return [_sanitize_string(str(item)) for item in data]
    elif isinstance(data, str):
        return _sanitize_string(data)
    else:
        return _sanitize_string(str(data))


class SafeLogger:
    """
    A wrapper around Python's logging.Logger that automatically sanitizes
    sensitive information before logging.
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def debug(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        msg = _sanitize_string(msg)
        args = tuple(_sanitize_string(str(a)) for a in args)
        self._logger.exception(msg, *args, **kwargs)
    
    # Delegate other attributes to the underlying logger
    def __getattr__(self, name):
        return getattr(self._logger, name)


def setup_logger(name: str, file_path: str, level=logging.DEBUG, 
                 enable_file_logging: bool = True,
                 enable_console_logging: bool = True) -> SafeLogger:
    """
    Sets up a logger with:
    - Optional file logging (plain text, no color)
    - Optional RichHandler for colored console output
    - Automatic sanitization of sensitive data
    Only sets up handlers once per logger.

    Args:
        name (str): Logger name (usually module name).
        file_path (str): Log file name to store logs.
        level (int): Logging level (e.g., logging.INFO).
        enable_file_logging (bool): Whether to log to file.
        enable_console_logging (bool): Whether to log to console.

    Returns:
        SafeLogger: Configured logger instance with sanitization.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers on repeated calls
    if not logger.handlers:
        # Setup file handler (logs to logs/<file_path>)
        if enable_file_logging:
            os.makedirs(LOGS_DIR, exist_ok=True)
            log_file_path = os.path.join(LOGS_DIR, file_path)
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        # Setup rich console handler (colored, timestamped output)
        if enable_console_logging:
            console_handler = RichHandler(
                rich_tracebacks=True,     # Enable colorful tracebacks
                show_time=True,           # Show time column
                show_level=True,          # Show level column
                show_path=True            # Show path to source
            )
            console_handler.setLevel(level)
            # No need to set a formatter; RichHandler handles formatting
            logger.addHandler(console_handler)

    # Wrap with SafeLogger for automatic sanitization
    return SafeLogger(logger)


# Convenience function for creating a safe logger
def get_logger(name: str) -> SafeLogger:
    """
    Get an existing logger by name, or create a new one if it doesn't exist.
    This is useful when you want to use the same logger across modules.
    
    Args:
        name: Name of the logger
        
    Returns:
        SafeLogger instance
    """
    if logging.getLogger(name).handlers:
        # Logger already exists, wrap it
        return SafeLogger(logging.getLogger(name))
    else:
        # Create a new logger with default settings
        return setup_logger(name, f"{name}.log", enable_file_logging=False)