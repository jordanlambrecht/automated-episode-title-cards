import logging
from logging.handlers import RotatingFileHandler
from load_config import config
from pathlib import Path


# Setup the logger during import
def setup_logger():
    """Setup logger with file rotation and console output based on config file."""

    log_file = config['logging']['log_file']
    max_log_size = config['logging']['max_log_size']
    backup_count = config['logging']['backup_count']
    console_log_level = getattr(logging, config['logging']['console_log_level'].upper())
    log_file_log_level = getattr(logging, config['logging']['log_file_log_level'].upper())

    logger = logging.getLogger("screenshot_maker")
    logger.setLevel(logging.DEBUG)  # Overall logger level (keep it at DEBUG for all handlers)

    # Create a rotating file handler to handle log rotation
    file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
    file_handler.setLevel(log_file_log_level)  # Set log level for the log file
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create a console handler to print logs to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)  # Set log level for the console
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Initialize and set up the logger on module load
logger = setup_logger()  # This makes sure the logger is always ready when imported