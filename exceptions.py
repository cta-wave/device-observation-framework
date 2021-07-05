# -*- coding: utf-8 -*-
"""Observation Framework specific exceptions.

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
Contributor: Eurofins Digital Product Testing UK Limited
"""

class ObsFrameError(Exception):
    """Base for specific exceptions thrown by Observation Framework.

    Args:
        message: A message.
    """

    def __init__(self, message: str):
        assert isinstance(message, str)
        self.__message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.__message


class ObsFrameTerminate(ObsFrameError):
    """Specific exceptions thrown by Observation Framework.
    when this is raised the Observation Framework will be terminated.
    """
    pass


class ConfigError(ObsFrameError):
    """Specific exception to indicate config errors"""
    pass
