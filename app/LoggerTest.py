import logging
import time


def custom_time(secs):
    # return local time + timezone offset
    return time.localtime(secs)


# Create format of the log
formatter = logging.Formatter(
    fmt="[%(asctime)s %(tz)s] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TZFilter(logging.Filter):
    def filter(self, record):
        record.tz = time.strftime("%z")
        return True


# Log file storage location
logger = logging.getLogger("myapp")
# Basic log level, you can set according to your requirements
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.addFilter(TZFilter())

# Add log handler
logger.addHandler(handler)

# Example of log entry
logger.info("Application started")
