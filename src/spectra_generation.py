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
import os
import shutil
from itertools import product

import numpy as np
from mako.template import Template

from src.rase_functions import _getCountsDoseAndSensitivity, get_sample_dir, \
    get_replay_input_dir, secondary_type, get_sample_spectra_filename, create_n42_file, \
    create_n42_file_from_template, rebin_ecal_disagreement
from src.rase_settings import RaseSettings
from src.contexts import SimContext
from src.table_def import Session, SampleSpectraSeed, BackgroundSpectrum, \
    ReplayTypes, DetectorInfluence
from sqlalchemy.exc import ArgumentError
import src.neutrons as neutron_functions


class SampleSpectraGeneration:
    """
    Generates Sample Spectra through its 'work' function
    This class is designed to be moved to a separate thread for background execution
    Signals are emitted for each sample generated and at the end of the process
    Execution can be stopped by setting self._abort to True
    """
    def __init__(self, sim_context_list: list[SimContext], test=False, samplepath=None):
        """
        @param sim_context_list: List of all (instrument,replay,scenario) combinations as SimContext objects
        @param test: Set to true for first spec gen when running the GUI to verify paths are right
        @param samplepath: If not the default sample specturm path
        """
        self.settings = RaseSettings()
        self.sim_context_list = sim_context_list
        if samplepath is None:
            self.sampleDir = self.settings.getSampleDirectory()
        else:
            self.sampleDir = os.path.join(samplepath, 'SampledSpectra')
        self.sampling_algo = self.settings.getSamplingAlgo()
        self.test = test
        self._abort = False

    def work(self):
        count = 0
        session = Session()

        # Since we need to use the same spectra for all replays,
        # inside the loop we will be grouping all replays associated with this scenario-detector
        # and therefore we want to keep track separately of which sim_contexts have already been processed
        processed_sim_contexts = []
        for sim_context in self.sim_context_list:
            if sim_context in processed_sim_contexts:
                continue

            detector = sim_context.detector
            scenario = sim_context.scenario
            replays = [sc.replay for sc in self.sim_context_list if sc.scenario == scenario and sc.detector == detector]

            processed_sim_contexts.extend([sc for sc in self.sim_context_list
                                           if sc.scenario == scenario and sc.detector == detector])

            if (detector.includeSecondarySpectrum and detector.secondary_type == secondary_type[
                'scenario'] and not scenario.scen_bckg_materials):
                continue

            sample_dir = get_sample_dir(self.sampleDir, detector, scenario.id)
            os.makedirs(sample_dir, exist_ok=True)
            for replay in replays:
                replay_input_dir = get_replay_input_dir(self.sampleDir, detector, replay, scenario.id)
                os.makedirs(replay_input_dir, exist_ok=True)

            # generate seed in order to later recreate sampleSpectra
            if (self.settings.getRandomSeed() != self.settings.getRandomSeedDefault()):
                seed = self.settings.getRandomSeed()
            else:
                seed = np.random.randint(0, pow(2, 30))
            sampleSeed = session.query(SampleSpectraSeed).filter_by(scen_id=scenario.id,
                                    det_name=detector.name).first() or SampleSpectraSeed(
                                    scen_id=scenario.id, det_name=detector.name)
            sampleSeed.seed = seed
            session.add(sampleSeed)
            session.commit()

            countsDoseAndSensitivity = _getCountsDoseAndSensitivity(scenario, detector)
            # Set appropriate secondary spectrum if needed
            # ???: if present, should distortions be applied to the secondary background? <SS>
            secondary_spectrum = None
            secondary_is_float = False
            if detector.includeSecondarySpectrum:
                secondary_spectrum = (session.query(BackgroundSpectrum).filter_by(
                    detector_name=detector.name)).first()
                if detector.secondary_type == secondary_type['scenario']:
                    # utilize background defined in the scenario for secondary background
                    secondary_spectrum = BackgroundSpectrum()
                    spec_info = []
                    for background, spectrum in product(scenario.scen_bckg_materials,
                                                        detector.base_spectra):
                        if background.material_name == spectrum.material_name:
                            cnts = rebin_ecal_disagreement(detector.ecal, spectrum.ecal, detector.chan_count,
                                                           spectrum.get_counts_as_np())
                            secondary_is_float = secondary_is_float or not all(
                                [float(k) == int(k) for k in cnts])
                            sens = spectrum.rase_sensitivity if background.fd_mode == 'DOSE' else \
                                spectrum.flux_sensitivity
                            spec_info.append({'counts': cnts, 'livetime': spectrum.livetime,
                                              'realtime': spectrum.realtime,
                                              'sens': sens, 'bkg_dose': background.dose})

                    secondary_spectrum.livetime = spec_info[0]['livetime']
                    secondary_spectrum.realtime = spec_info[0]['realtime']
                    for s in spec_info:
                        if s['livetime'] > secondary_spectrum.livetime:
                            secondary_spectrum.livetime = s['livetime']
                            secondary_spectrum.realtime = s['realtime']
                    # use max livetime of scenario bgnd specs unless bckg_spectra_dwell specified
                    if detector.bckg_spectra_dwell != 0:
                        secondary_spectrum.realtime = detector.bckg_spectra_dwell * (
                                    secondary_spectrum.realtime /
                                    secondary_spectrum.livetime)
                        secondary_spectrum.livetime = detector.bckg_spectra_dwell
                    secondary_spectrum.counts = np.zeros(len(spec_info[0]['counts']))
                    for s in spec_info:
                        secondary_spectrum.counts += secondary_spectrum.livetime * s['sens'] * \
                                                     s['bkg_dose'] * \
                                                     (s['counts'] / np.sum(s['counts']))
                    secondary_spectrum.ecal  = detector.ecal
                    secondary_spectrum.ecal0 = detector.ecal0
                    secondary_spectrum.ecal1 = detector.ecal1
                    secondary_spectrum.ecal2 = detector.ecal2
                    secondary_spectrum.ecal3 = detector.ecal3
                    secondary_spectrum.neutrons = (neutron_functions.neutron_background(scenario,detector, secondary_spectrum.livetime))[1] # [1] because this function returns counts & expectation, and we'll poisson sample the expectation later
                else:
                    secondary_is_float = not all(
                        [float(k) == int(k) for k in secondary_spectrum.counts])
                    if detector.bckg_spectra_dwell != 0:
                        secondary_spectrum.counts *= detector.bckg_spectra_dwell / \
                                                     secondary_spectrum.livetime
                        #TODO: neutrons
                        secondary_spectrum.realtime = detector.bckg_spectra_dwell * (
                                                    secondary_spectrum.realtime /
                                                    secondary_spectrum.livetime)
                        secondary_spectrum.livetime = detector.bckg_spectra_dwell
                        secondary_spectrum.neutrons *= detector.bckg_spectra_dwell / \
                                                       secondary_spectrum.livetime
                    secondary_spectrum.counts = rebin_ecal_disagreement(detector.ecal, secondary_spectrum.ecal,
                                                                        detector.chan_count, secondary_spectrum.counts)

            # create 'replication' number of files
            reps = 1 if self.test else scenario.replication
            for filenum in range(reps):
                # This is where the downsampling happens
                if secondary_spectrum and detector.bckg_spectra_resample:
                    if filenum == 0:
                        secondary_is_float = secondary_spectrum.is_spectrum_float()
                        original_secondary_spe_counts = secondary_spectrum.counts
                        original_secondary_spe_neutrons = secondary_spectrum.neutrons
                    secondary_spectrum.counts = np.random.poisson(original_secondary_spe_counts)
                    secondary_spectrum.neutrons = np.random.poisson(original_secondary_spe_neutrons)
                if secondary_spectrum and not secondary_is_float:
                    secondary_spectrum.counts = secondary_spectrum.counts.astype(int)
                    secondary_spectrum.neutrons = secondary_spectrum.neutrons.astype(int)

                degradations = []
                for influence in scenario.influences:
                    influences = session.query(DetectorInfluence).filter_by(
                        influence_name=influence.name).first()
                    degradations.append([a * (filenum) for a in
                                         [influences.degrade_infl0, influences.degrade_infl1,
                                          influences.degrade_infl2, influences.degrade_f_smear,
                                          influences.degrade_l_smear]])
                    # If there is some degradation, we pass them in to apply degradations without
                    # doing it exponentially
                if not all(v == 0 for deg in degradations for v in deg):
                    countsDoseAndSensitivity = _getCountsDoseAndSensitivity(scenario, detector,
                                                                            degradations)

                sampleCounts = self.sampling_algo(scenario, detector, countsDoseAndSensitivity,
                                                  seed + filenum)
                neutronsample, neutron_expectation = neutron_functions.neutron_foreground(scenario,detector)

                # write out to RASE n42 file
                fname = os.path.join(sample_dir,
                                     get_sample_spectra_filename(detector.id, scenario.id,
                                                                 filenum, ".n42"))
                create_n42_file(fname, scenario, detector, sampleCounts, secondary_spectrum, neutrons=neutronsample)

                for replay in replays:
                    # write out to translated file format
                    if replay and replay.type == ReplayTypes.standalone and replay.n42_template_path:
                        n42_template = Template(filename=replay.n42_template_path, input_encoding='utf-8')
                        replay_input_dir = get_replay_input_dir(self.sampleDir, detector, replay, scenario.id)
                        fname = os.path.join(replay_input_dir,get_sample_spectra_filename(
                            detector.id, scenario.id, filenum, replay.input_filename_suffix))
                        create_n42_file_from_template(n42_template, fname, scenario, detector,
                                                      sampleCounts, secondary_spectrum, neutrons=neutronsample)

                        if self._abort:
                            # delete current folders since generation was incomplete
                            if os.path.exists(sample_dir):
                                shutil.rmtree(sample_dir)
                            if os.path.exists(replay_input_dir):
                                shutil.rmtree(replay_input_dir)
                            break

                count += (max(len(replays),1))
                self._gui_sigstep_emit(count)
                self._gui_process_events()
                # check if we need to abort the loop; need to process events to receive signals;

        session.close()
        self._gui_sigdone_emit()


    def _gui_process_events(self):
        pass

    def _gui_sigstep_emit(self, count):
        pass

    def _gui_sigdone_emit(self):
        pass

    def abort(self):
        self._abort = True
