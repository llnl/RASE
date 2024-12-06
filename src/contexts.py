###############################################################################
# Copyright (c) 2018-2024 Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
#
# Written by J. Brodsky, J. Chavez, S. Czyz, G. Kosinovsky, V. Mozin,
#            S. Sangiorgio.
#
# RASE-support@llnl.gov.
#
# LLNL-CODE-2001375, LLNL-CODE-829509
#
# All rights reserved.
#
# This file is part of RASE.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED,INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
###############################################################################
"""
This module defines the service class for RASE workflow execution.
"""
from dataclasses import dataclass

from src.table_def import Detector, Replay, Scenario


@dataclass
class SimContext:
    """Class for holding the detector-replay-scenario of each simulation in RASE"""
    detector: Detector
    replay: Replay
    scenario: Scenario

    def __repr__(self):
        det_txt = self.detector.name if self.detector else None
        rep_txt = self.replay.name if self.replay else None
        scen_txt = self.scenario.id if self.scenario else None
        return f"Detector={det_txt}, Replay={rep_txt}, Scenario={scen_txt}"

    def __eq__(self, other):
        if isinstance(other, SimContext):
            return self.detector is other.detector and self.replay is other.replay and self.scenario is other.scenario
        return False

    def __hash__(self):
        # needed so it can be used in sets and dictionary keys
        return hash((self.detector.id, self.replay.id, self.scenario.id))

