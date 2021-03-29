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
Licensor: Eurofins Digital Product Testing UK Limited
"""
import logging
from logging.handlers import RotatingFileHandler

MAX_LOGFILE_BYTES = 10 * 1024 * 1024
BAK_LOG_FILE_NUM = 5


def create_logger(log_file: str, loglevel: str) -> None:
    """Create logger handlers for the logfiles and the console output

    Args:
        log_file (str): path to the logfile to use.
        loglevel (str): logging level for the file's output

    Raises:
        ValueError on logging.basicConfig failures
    """
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)

    # send requested logging level and higher logging to a rotating logfile
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(
                log_file, maxBytes=MAX_LOGFILE_BYTES, backupCount=BAK_LOG_FILE_NUM
            )
        ],
        level=numeric_level,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M",
    )

    # define a Handler which writes INFO messages and higher to sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)
