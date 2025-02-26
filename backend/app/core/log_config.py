import logging
import sys


def set_logging_options(level: int) -> None:
    """Set the logging options based on the level parameter.

    Parameters
    ----------
    level : int
        Logging level. 0: WARNING, 1: INFO, 2: DEBUG
    """
    # Validate the level input
    if level not in [0, 1, 2]:
        raise ValueError(f"Invalid log level {level}. Must be one of [0, 1, 2].")

    # Map the input level to logging constants
    level_mapping = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    log_level = level_mapping[level]

    # Remove all existing handlers from the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    log_format = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d:%(funcName)s(): %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set the handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    for handler in handlers:
        handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
        logging.root.addHandler(handler)

    # Set the logging level for the root logger to the mapped level
    logging.root.setLevel(log_level)

