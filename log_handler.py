# -*- coding: utf-8 -*-
"""Utilities to handle logging.

The Software is provided to you by the Licensor under the License, as
defined below, subject to the following condition.

Without limiting other conditions in the License, the grant of rights under
the License will not include, and the License does not grant to you, the
right to Sell the Software.

For purposes of the foregoing, “Sell” means practicing any or all of the
rights granted to you under the License to provide to third parties, for a
fee or other consideration (including without limitation fees for hosting
or consulting/ support services related to the Software), a product or
service whose value derives, entirely or substantially, from the
functionality of the Software. Any license notice or attribution required
by the License must also include this Commons Clause License Condition
notice.

Software: WAVE Observation Framework
License: Apache 2.0 https://www.apache.org/licenses/LICENSE-2.0.txt
Licensor: Consumer Technology Association
Contributor: Resillion UK Limited
"""
import logging
from logging import FileHandler
from logging.handlers import RotatingFileHandler

MAX_LOGFILE_BYTES = 10 * 1024 * 1024
BAK_LOG_FILE_NUM = 5


class LogManager:
    """Log Manager class"""

    _logger_handler: FileHandler
    """log file handler"""
    _file_formatter: logging.Formatter

    def __init__(self, log_file: str, loglevel: str, console_loglevel: str):
        """Create logger handlers for the log files and the console output

        Args:
            log_file (str): path to the logfile to use.
            loglevel (str): logging level for the file's output

        Raises:
            ValueError on logging.basicConfig failures
        """
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {loglevel}")
        numeric_level_console = getattr(logging, console_loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {console_loglevel}")

        self._logger_handler = RotatingFileHandler(
            log_file, maxBytes=MAX_LOGFILE_BYTES, backupCount=BAK_LOG_FILE_NUM
        )
        self._file_formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M",
        )

        # send requested logging level and higher logging to a rotating logfile
        logging.basicConfig(
            handlers=[self._logger_handler],
            level=numeric_level,
            format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M",
        )

        # define a Handler which writes INFO messages and higher to sys.stderr
        console = logging.StreamHandler()
        console.setLevel(numeric_level_console)
        formatter = logging.Formatter("%(levelname)-8s %(message)s")
        console.setFormatter(formatter)
        logging.getLogger("").addHandler(console)

    def redirect_logfile(self, session_log_name: str):
        """redirect log file to <session-id>.log
        Args:
            session_log_name (str): path to the logfile to use.
        """
        file_handler = FileHandler(session_log_name)
        file_handler.setFormatter(self._file_formatter)
        logging.getLogger("").addHandler(file_handler)
        logging.getLogger("").removeHandler(self._logger_handler)
        self._logger_handler.close()
        self._logger_handler = file_handler

    def setup_session_logger(self, session_log_name: str, session_id: str):
        """set up session specific logger"""
        logger = logging.getLogger(session_id)
        file_handler = FileHandler(session_log_name)
        file_handler.setFormatter(self._file_formatter)
        logger.propagate = False
        logger.addHandler(file_handler)
