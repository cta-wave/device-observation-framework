# -*- coding: utf-8 -*-
"""observation every_sample_rendered_in_cmaf_presentation

make observation of every_sample_rendered_in_cmaf_presentation

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
from .every_sample_rendered import EverySampleRendered
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)


class EverySampleRenderedInCMAFPresentation(EverySampleRendered):
    """EverySampleRenderedInCMAFPresentation class
    Every sample for every media type included in the CMAF Presentation duration shall be rendered
    and shall be rendered in order.
    Video only for phase one
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            global_configurations,
            "[OF] Video only: Every sample for every media type included in the CMAF Presentation duration "
            "shall be rendered and shall be rendered in order.",
        )
