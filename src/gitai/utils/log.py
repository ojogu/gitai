# log_util.py
import logging
import os
from rich.logging import RichHandler  # Rich handler for colored console output

# Determine the root directory of the project.
# This script is in: src/gitai/utils/log.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")


def setup_logger(name: str, file_path: str, level=logging.DEBUG) -> logging.Logger:
    """
    Sets up a logger with:
    - File logging (plain text, no color)
    - RichHandler for colored console output
    Only sets up handlers once per logger.

    Args:
        name (str): Logger name (usually module name).
        file_path (str): Log file name to store logs.
        level (int): Logging level (e.g., logging.INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers on repeated calls
    if not logger.handlers:
        os.makedirs(LOGS_DIR, exist_ok=True)

        # Setup file handler (logs to logs/<file_path>)
        log_file_path = os.path.join(LOGS_DIR, file_path)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Setup rich console handler (colored, timestamped output)
        console_handler = RichHandler(
            rich_tracebacks=True,     # Enable colorful tracebacks
            show_time=True,           # Show time column
            show_level=True,          # Show level column
            show_path=True            # Show path to source
        )
        console_handler.setLevel(level)
        # No need to set a formatter; RichHandler handles formatting

        # Add both handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger