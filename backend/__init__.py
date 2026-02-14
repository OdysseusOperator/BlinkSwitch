import logging
import os
import sys
from datetime import datetime


# Set up logging
def setup_logging(log_file=None):
    """Set up logging for the application.

    Args:
        log_file (str, optional): Path to log file. If None, uses default location.
    """
    if log_file is None:
        # Default log file in the same directory as the script
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"screenassign_{timestamp}.log")

    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    # Create a logger for this module
    logger = logging.getLogger("ScreenAssign")
    logger.info(f"Logging initialized to {log_file}")

    return logger


# Version information
__version__ = "1.0.0"
