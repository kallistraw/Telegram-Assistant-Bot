import logging
import os
import time

# Ensure the logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Define log retention period (in days)
LOG_RETENTION_DAYS = 7

# TODO: create a module to clean logs
# Cleanup function
def clean_old_logs():
    """Deletes log files older than LOG_RETENTION_DAYS."""
    now = time.time()
    for filename in os.listdir(LOG_DIR):
        file_path = os.path.join(LOG_DIR, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > LOG_RETENTION_DAYS * 86400:  # Convert days to seconds
                os.remove(file_path)
                print(f"🗑️ Deleted old log: {filename}")

# Run cleanup on startup
clean_old_logs()

# Create logger instance
log = logging.getLogger("BotLogger")
log.setLevel(logging.DEBUG)

# File handler (creates a new log file each day)
log_filename = os.path.join(LOG_DIR, time.strftime("%Y-%m-%d.log"))
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
log.addHandler(file_handler)
log.addHandler(console_handler)