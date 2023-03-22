import logging
from logging.handlers import SysLogHandler

LOG_FORMAT = "%(asctime)s.%(msecs)d %(lineno)d %(levelname)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

def get_logger(
        prog_name=None,
        log_file=None,
        debug_mode=False,
        syslog=None) -> logging.Logger:
    # log_file: a file name for logging.
    #           `-` means to show log onto stdout.
    #           `syslog` means to use syslog.
    # debug_mode: set log level to DEBUG, otherwise set to INFO.
    # syslog: syslog server's address
    def get_logging_handler(channel):
        channel.setFormatter(logging.Formatter(fmt=LOG_FORMAT,
                                               datefmt=LOG_DATE_FORMAT))
        if debug_mode:
            channel.setLevel(logging.DEBUG)
        else:
            channel.setLevel(logging.INFO)
        return channel

    logger = logging.getLogger(prog_name)
    if log_file == "-":
        logger.addHandler(get_logging_handler(logging.StreamHandler()))
    elif log_file == "syslog":
        logger.addHandler(SysLogHandler(address=syslog))
    elif log_file is not None:
        logger.addHandler(get_logging_handler(logging.FileHandler(log_file)))

    if debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.info("enabled DEBUG mode")
    else:
        logger.setLevel(logging.INFO)

    return logger

