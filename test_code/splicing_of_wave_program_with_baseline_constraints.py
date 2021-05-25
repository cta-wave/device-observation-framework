# -*- coding: utf-8 -*-
"""DPCTF device observation test code 
splicing_of_wave_program_with_baseline_constraints

test splicing_of_wave_program_with_baseline_constraints

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
from .playback_over_wave_baseline_splice_constraints import PlaybackOverWaveBaselineSpliceConstraints

logger = logging.getLogger(__name__)


class SplicingOfWaveProgramWithBaselineConstraints(PlaybackOverWaveBaselineSpliceConstraints):
    """SplicingOfWaveProgramWithBaselineConstraints to handle test 
    splicing-of-wave-program-with-baseline-constraints.html.
    This class is derived from PlaybackOverWaveBaselineSpliceConstraints and uses the same observations logic.
    """

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            ("every_sample_rendered_in_cmaf_presentation", "EverySampleRenderedInCMAFPresentation"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("earliest_sample_same_presentation_time", "EarliestSampleSamePresentationTime"),
        ]
