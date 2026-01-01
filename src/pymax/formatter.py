import logging
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    COLORS: ClassVar = {
        "DEBUG": "\033[37m",
        "INFO": "\033[36m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }

    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, self.RESET)
        time_color = self.DIM
        name_color = "\033[35m"
        message_color = self.RESET

        log = (
            f"{time_color}{self.formatTime(record, '%H:%M:%S')}{self.RESET} "
            f"[{level_color}{record.levelname}{self.RESET}] "
            f"{name_color}{record.name}{self.RESET}: "
            f"{message_color}{record.getMessage()}{self.RESET}"
        )

        if record.exc_info and record.exc_info[0] is not None:
            log += "\n" + self.formatException(record.exc_info)

        return log
