import logging
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.logging import RichHandler
from pathlib import Path
from .load_config import config
from rich.traceback import install
import json
import traceback

# Ensure the log directory exists
log_dir = Path("./log")
log_dir.mkdir(parents=True, exist_ok=True)

# Set up Rich console
console = Console()

# Enable Rich's pretty traceback globally for all unhandled exceptions
install(show_locals=True)

# Setup the logger during import
def setup_logger():
    """Setup logger with file rotation and console output based on config file."""

    log_file = log_dir / config['logging']['log_file']  # Log file in ./log directory
    max_log_size = config['logging']['max_log_size'] * 1024  # Convert KB to bytes
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

    # Use RichHandler for console logging
    console_handler = RichHandler(show_path=False)
    console_handler.setLevel(console_log_level)  # Set log level for the console
    logger.addHandler(console_handler)

    return logger

# Initialize and set up the logger on module load
logger = setup_logger()  # This makes sure the logger is always ready when imported

# Centralized logging and error handling

class LogMessage:
    def __init__(self, logger):
        self.logger = logger
        # Retrieve log levels from the config
        self.console_log_level = getattr(logging, config['logging']['console_log_level'].upper())
        self.log_file_log_level = getattr(logging, config['logging']['log_file_log_level'].upper())

    def message(self, message, style = ""):
        console.print(f"{message}", style=style)

    def error(self, message):
        """Log an error message both to the console and file."""
        if logging.ERROR >= self.log_file_log_level:
            self.logger.error(message)
        if logging.ERROR >= self.console_log_level:
            console.print(f"❗️ ERROR: {message}", style="bold red")

    def info(self, message):
        """Log an info message both to the console and file."""
        if logging.INFO >= self.log_file_log_level:
            self.logger.info(message)
        if logging.INFO >= self.console_log_level:
            console.print(f"ℹ️ INFO: {message}", style="bold green")

    def warning(self, message):
        """Log a warning message both to the console and file."""
        if logging.WARNING >= self.log_file_log_level:
            self.logger.warning(message)
        if logging.WARNING >= self.console_log_level:
            console.print(f"⚠️ WARNING: {message}", style="bold yellow")

    def debug(self, message):
        """Log a debug message both to the console and file."""
        if logging.DEBUG >= self.log_file_log_level:
            self.logger.debug(message)
        if logging.DEBUG >= self.console_log_level:
            console.print(f"🔍 DEBUG: {message}", style="bold blue")

    def log_structured(self, data):
        """Log structured data as JSON for debugging or analysis purposes."""
        json_data = json.dumps(data, indent=4)
        self.debug(f"Structured Data:\n{json_data}")

# Error handler with stack trace logging
def error(message: str):
    """
    Handles error logging and prints the error message and stack trace to the log file.

    :param message: The error message to display and log
    """
    console.print(f"❗️ ERROR: {message}", style="bold red")
    logger.error(f"{message}\n{traceback.format_exc()}")  # Log with stack trace

# Create a global instance for logging
log_message = LogMessage(logger)