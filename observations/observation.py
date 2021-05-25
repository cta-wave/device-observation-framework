# -*- coding: utf-8 -*-
"""observation base class

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
import logging

from typing import Dict
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)


class Observation:
    """Observation base class"""

    result: Dict[str, str]
    """observation result
    status: NOT_RUN | PASS | FAIL
    message: observation message this will be displayed on test runner
    name: description of the observation
    """
    tolerances: Dict[str, int]
    """tolerances of the observation
    this is configured in CONFIG.INI file
    """
    missing_frame_threshold: int
    """Threshold of missing frame.
    If the number of missing frames on an individual test is greater than this 
    post error messege and terminate the session.
    """

    def __init__(self, name: str, global_configurations: GlobalConfigurations = None):
        self.result = {
            "status": "NOT_RUN",
            "message": "",
            "name": name,
        }

        if global_configurations is None:
            self.tolerances = {}
            self.missing_frame_threshold = 0
        else:
            self.tolerances = global_configurations.get_tolerances()
            self.missing_frame_threshold = global_configurations.get_missing_frame_threshold()
