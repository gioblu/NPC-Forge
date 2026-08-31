import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path

# Define the base directory path
BASE_DIR = "~/.local/share/npc-forge"

# Convert to an absolute Path by expanding the user tilde
FORGE_DATA_DIR = Path(BASE_DIR).expanduser()

# Configure the log target file path
log_file_path = FORGE_DATA_DIR / "logs" / "npc_forge.log"

# Automatically create the 'logs' folder and its parents if they don't exist
log_file_path.parent.mkdir(exist_ok=True)

# Create a master logger instance
logger = logging.getLogger("npc_forge")
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if the logger is imported across multiple files
if not logger.handlers:
    # Define a shared uniform format style for logs
    formatter = logging.Formatter(
        '|%(asctime)s|%(levelname)s|%(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Rotating File Handler (Rotates daily at midnight, keeps last 30 days)
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",     # Trigger rotation at midnight
        interval=1,          # Interval set to 1 day
        backupCount=30,      # Automatically keep the last 30 log files (one month)
        encoding="utf-8"
    )
    # Suffix format (e.g., npc_forge.log.2026-07-27)
    file_handler.suffix = "%Y-%m-%d" 
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream Handler (Keeps logs visible inside the terminal screen simultaneously)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
