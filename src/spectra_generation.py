###############################################################################
# Copyright (c) 2018-2026 Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
#
# Written by J. Brodsky, J. Chavez, S. Czyz, G. Kosinovsky, V. Mozin,
#            S. Sangiorgio.
#
# RASE-support@llnl.gov.
#
# LLNL-CODE-2014600, LLNL-CODE-829509
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
import yaml

from itertools import product
from pathlib import Path

import numpy as np
from mako.template import Template
from sqlalchemy.orm import make_transient

from src.rase_functions import get_sample_dir, get_replay_input_dir, secondary_type, get_sample_spectra_filename, \
                                create_n42_file, create_n42_file_from_template, rebin_ecal_disagreement, \
                                find_nearest_inlist, apply_distortions, calculate_influence
from src.create_shielded_spectra_dialog import ShieldingModule
from src.rase_settings import RaseSettings
from src.contexts import SimContext
from src.table_def import Session, SampleSpectraSeed, Spectrum, BaseSpectrum, SecondarySpectrum, ShieldedSpectrum, \
                           ReplayTypes, DetectorInfluence, Detector, Scenario, Replay
from sqlalchemy.exc import ArgumentError
import src.neutrons as neutron_functions
from src.qt_utils import Translatable


class SampleSpectraGeneration(Translatable):
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
        if samplepath is None:
            self.sampleDir = self.settings.getSampleDirectory()
        else:
            self.sampleDir = os.path.join(samplepath, 'SampledSpectra')
        self.sampling_algo = self.settings.getSamplingAlgo()
        self.test = test
        self._abort = False

        # ORM objects cannot be safely passed between threads so we extract the necessary data from the sim_context_list
        # and store it in the class so it can be recreated later in the work() function in a thread-local session
        self.sim_context_list_data = [(sc.detector.id, sc.scenario.id, sc.replay.id if sc.replay is not None else None)
                                      for sc in sim_context_list]
        # Also, make objects transient so they are no longer associated with the parent session
        # and therefore are not removed when the session is closed in the work() function
        for sc in sim_context_list:
            for obj in sc.detector, sc.replay, sc.scenario:
                if obj is not None:
                    make_transient(obj)
        self._gen_shielded_specs()


    def _gen_shielded_specs(self):
        """
        Generate and persist shielded base spectra for scenarios that define shielding.

        For each (detector, scenario) pair in `self.sim_context_list_data` with a
        shielding material and thickness, compute the shielded response for using the
        configured shielding models/DRFs (interpolating when needed). Results are stored
        as `ShieldedSpectrum` rows for reuse during sampling.
        """
        session = Session()
        with open(self.settings.getShieldingPathConfig(), mode='r') as file:
            configs = yaml.safe_load(file)  # paths to shielding .npz files
        for detector_id, scenario_id, replay_id in self.sim_context_list_data:
            detector = session.get(Detector, detector_id)
            scenario = session.get(Scenario, scenario_id)
            if scenario.shielding_material and scenario.shielding_thickness:
                for spec in scenario.scen_materials:
                    shielded_spec = session.query(ShieldedSpectrum).filter_by(detector_name=detector.name,
                                                              material_name=spec.material_name,
                                                              shielding_material=scenario.shielding_material,
                                                              shielding_thickness=scenario.shielding_thickness).first()
                    if shielded_spec is None:
                        print(f'Making shielding for {detector.name}, {spec.material_name}')
                        try:
                            baseSpectrum = session.query(BaseSpectrum).filter_by(detector_name=detector.name,
                                                                             material_name=spec.material_name).first()
                            configs_inst = Path(configs['inst_configs'])
                            configs_null = Path(configs['shield_configs'])
                            drf_options = configs.get(detector.chan_count)
                            if drf_options is None:
                                raise Exception(
                                    self.tr('Using a detector with a # of channels {} that is incompatible with '
                                            'preloaded library'.format(detector.chan_count)))
                            drf = detector.shielding_drf if detector.shielding_drf else list(drf_options.keys())[0]
                            drf_ecals = drf_options[drf].get('ecals')
                            shield_model = ShieldingModule(detector.name, detector.chan_count, drf_ecals,
                                                           configs['inst_configs'], configs['shield_configs'])
                            shield_mat_dict = drf_options[drf][scenario.shielding_material]

                            path_drfinv = configs_inst / str(detector.chan_count) / drf_options[drf][drf + '_inv']
                            path_drf = configs_inst / str(detector.chan_count) / drf_options[drf][drf]
                            path_nullinv = configs_null / str(detector.chan_count) / drf_options[drf]['null_inv']

                            interp_bounds = find_nearest_inlist([float(x[:-2]) for x in list(shield_mat_dict.keys())],
                                                                scenario.shielding_thickness)
                            interp_bounds = [int(ib) if float(ib) == int(float(ib)) else float(ib) for ib in
                                             interp_bounds]

                            if len(interp_bounds) > 1:  # interpolation
                                path_nullshield_lower = (configs_null / str(detector.chan_count) / drf_options[drf][
                                    scenario.shielding_material][str(interp_bounds[0]) + 'cm'])
                                path_nullshield_upper = (configs_null / str(detector.chan_count) / drf_options[drf][
                                    scenario.shielding_material][str(interp_bounds[1]) + 'cm'])
                                null_responses_lower, drf_responses = shield_model.load_responses(path_nullinv,
                                                                        path_nullshield_lower, path_drfinv, path_drf)
                                null_responses_upper, _ = shield_model.load_responses(path_nullinv,
                                                                        path_nullshield_upper, path_drfinv, path_drf)
                                matrices = {interp_bounds[0]: path_nullshield_lower,
                                            interp_bounds[1]: path_nullshield_upper}
                                T = shield_model.interpolate_response(scenario.shielding_thickness, matrices,
                                                                      path_nullinv)
                                outcounts = shield_model.get_outcounts(T, drf_responses, baseSpectrum)
                            else:  # exact
                                path_nullshield = (configs_null / str(detector.chan_count) / drf_options[drf][
                                    scenario.shielding_material][str(interp_bounds[0]) + 'cm'])
                                null_responses, drf_responses = shield_model.load_responses(path_nullinv,
                                                                                            path_nullshield,
                                                                                            path_drfinv, path_drf)
                                outcounts = shield_model.process_matrices(null_responses, drf_responses, baseSpectrum)

                            baseSpectrum = shield_model.build_base_spectrum(outcounts, baseSpectrum)
                            # commit to session
                            new_shielded_spec = ShieldedSpectrum(baseSpectrum, detector_name=detector.name,
                                                                 spectrum_type='shielded_spectrum',
                                                                 shielding_material=scenario.shielding_material,
                                                                 shielding_thickness=scenario.shielding_thickness)
                            session.add(new_shielded_spec)
                            session.commit()
                        except FileNotFoundError as e:
                            raise FileNotFoundError(self.tr('Could not load shielding paths from config path. '
                                                            'Full error: {}'.format(e)))

    def get_sim_context_from_ids(self, session):
        """
        Recreate the sim_context_list from the stored data
        """
        sim_context_list = []
        for detector_id, scenario_id, replay_id in self.sim_context_list_data:
            detector = session.get(Detector, detector_id)
            scenario = session.get(Scenario, scenario_id)
            replay = session.get(Replay, replay_id) if replay_id is not None else None
            sim_context_list.append(SimContext(detector=detector, replay=replay, scenario=scenario))
        return sim_context_list

    def work(self):
        count = 0

        # use local thread session
        with Session() as session:

            # reload the sim_context_list from the stored data
            sim_context_list = self.get_sim_context_from_ids(session)

            # Since we need to use the same spectra for all replays,
            # inside the loop we will be grouping all replays associated with this scenario-detector
            # and therefore we want to keep track separately of which sim_contexts have already been processed
            processed_sim_contexts = []
            for sim_context in sim_context_list:
                if sim_context in processed_sim_contexts:
                    continue

                detector = sim_context.detector
                scenario = sim_context.scenario
                replays = [sc.replay for sc in sim_context_list if sc.scenario == scenario and sc.detector == detector and sc.replay]

                processed_sim_contexts.extend([sc for sc in sim_context_list
                                               if sc.scenario == scenario and sc.detector == detector])

                if (detector.includeSecondarySpectrum
                        and detector.secondary_type == secondary_type['scenario']
                        and not scenario.scen_bckg_materials):
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
                countsDoseAndSensitivity = self._getCountsDoseAndSensitivity(scenario, detector)
                # Set appropriate secondary spectrum if needed
                # ???: if present, should distortions be applied to the secondary background? <SS>
                secondary_spectrum = None
                secondary_is_float = False
                if detector.includeSecondarySpectrum:
                    secondary_spectrum = detector.bckg_spectrum #for cases where the spectrum is just stored in the detector
                    if detector.secondary_type == secondary_type['scenario']: #building it from the scenario instead
                        # utilize background defined in the scenario for secondary background
                        secondary_spectrum = Spectrum()
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
                        secondary_spectrum.neutrons = int(secondary_spectrum.neutrons)  # should always be just one number

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
                        countsDoseAndSensitivity = self._getCountsDoseAndSensitivity(scenario, detector,
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
        self._gui_sigdone_emit()


    def _gui_process_events(self):
        pass

    def _gui_sigstep_emit(self, count):
        pass

    def _gui_sigdone_emit(self):
        pass

    def abort(self):
        self._abort = True

    @classmethod
    def _getCountsDoseAndSensitivity(self, scenario, detector, degradations=None):
        """

        :param scenario:
        :param detector:
        :return:
        """
        session = Session()

        ecal = detector.ecal

        new_influences, bin_widths, energies = calculate_influence(scenario, detector, degradations, ecal)

        # get dose, counts and sensitivity for each material
        countsDoseAndSensitivity = []
        for scenMaterial in scenario.scen_materials + scenario.scen_bckg_materials:
            if scenMaterial in scenario.scen_materials and scenario.shielding_material and scenario.shielding_thickness:
                baseSpectrum = session.query(ShieldedSpectrum).filter_by(detector_name=detector.name,
                                                             material_name=scenMaterial.material_name,
                                                             shielding_material=scenario.shielding_material,
                                                             shielding_thickness=scenario.shielding_thickness).first()
            else:
                baseSpectrum = session.query(BaseSpectrum).filter_by(detector_name=detector.name,
                                                                 material_name=scenMaterial.material_name).first()
            counts = rebin_ecal_disagreement(ecal, baseSpectrum.ecal, detector.chan_count, baseSpectrum.counts)

            if scenario.influences:
                for index, infl in enumerate(new_influences):
                    counts = apply_distortions(infl, counts, bin_widths[index], energies, ecal)

            if scenMaterial.fd_mode == 'FLUX':
                countsDoseAndSensitivity.append((counts, scenMaterial.dose, baseSpectrum.flux_sensitivity))
            else:
                countsDoseAndSensitivity.append((counts, scenMaterial.dose, baseSpectrum.rase_sensitivity))

        # if the detector has an internal calibration source, it needs to be added with special treatment
        if detector.includeSecondarySpectrum and detector.sample_intrinsic:

            secondary_spectra = session.query(SecondarySpectrum).filter_by(detector_name=detector.name).all()
            secondary_spectrum = [k for k in secondary_spectra if k.classcode == detector.intrinsic_classcode][0]
            counts = rebin_ecal_disagreement(ecal, secondary_spectra.ecal, detector.chan_count,
                                             secondary_spectrum.get_counts_as_np())

            # apply distortion on counts
            if scenario.influences:
                for index, infl in enumerate(new_influences):
                    counts = apply_distortions(infl, counts, bin_widths[index], energies, ecal)

            # extract counts per second
            cps = sum(counts) / secondary_spectrum.livetime

            # the internal calibration spectrum is scaled only by time
            # so the sensitivity parameter is set to the cps and the dose to 1
            countsDoseAndSensitivity.append((counts, 1.0, cps))

        return countsDoseAndSensitivity
