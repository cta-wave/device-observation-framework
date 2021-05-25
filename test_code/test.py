# -*- coding: utf-8 -*-
""" Defines test types

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
from enum import Enum


class TestType(Enum):
    """TestType Enum
    SEQUENTIAL: general playback test with contents played back from starting point to the end.
    SWITCHING: switching test that contents switches between representations.
    SPLICING: splicing test which is concatenates different content at any point during the playback.
        The original content may then be returned to (such as an advert insertion test).
    """

    SEQUENTIAL = 1
    SWITCHING = 2
    SPLICING = 3
