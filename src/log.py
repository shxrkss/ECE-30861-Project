import os
import logging

def setup_logging():
    log_file = os.getenv("LOG_FILE", "logfile.log")
    log_level = int(os.getenv("LOG_LEVEL", "0"))

    if log_level == 0:
        level = logging.CRITICAL
    elif log_level == 1:
        level = logging.INFO
    elif log_level == 2:
        level = logging.DEBUG
    else:
        level = logging.CRITICAL  # fallback if invalid value

    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )


def log_messages_test():
    logging.critical("This is a critical message.")  # Will be logged if log_level >= 0
    logging.info("This is an informational message.")  # Will be logged if log_level >= 1
    logging.debug("This is a debug message.")  # Will be logged if log_level == 2
