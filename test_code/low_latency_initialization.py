"""DPCTF device observation test code low_latency_initialization

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

from .mse_append_window import MseAppendWindow


class LowLatencyInitialization(MseAppendWindow):
    """LowLatencyInitialization to handle test low-latency-initialization.html
    Derived from MseAppendWindow test code. Uses same logic.
    """

    def _init_parameters(self) -> None:
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "render_threshold",
        ]

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            ("every_sample_rendered", "EverySampleRendered"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
            ("rendering_delay_within_threshold", "RenderingDelayWithinThreshold"),
        ]
