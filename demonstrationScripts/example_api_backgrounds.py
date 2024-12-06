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
import sys
import os
import pathlib

os.chdir(pathlib.Path(__file__).parent.parent.resolve())

print(os.getcwd())
# sys.path.append('..\\')
sys.path.append(os.getcwd())
sys.path.append(os.getcwd()+'\\tests')

from pathlib import Path
import yaml
from tqdm import tqdm

from src.rase_init import init_rase
from src.base_spectra_dialog import BaseSpectraLoadModel
from src.contexts import SimContext
from src.replay_dialog import ReplayModel
from src.detector_dialog import DetectorModel
from src.scenario_dialog import ScenarioModel
from src.spectra_generation import SampleSpectraGeneration
from src.replay_generation import ReplayGeneration, TranslationGeneration
from src.results_calculation import calculateScenarioStats, export_results
# from tests.fixtures import HelpObjectCreation
from src.table_def import Material, Scenario, ScenarioBackgroundMaterial, Session
try:
    from tests.fixtures import HelpObjectCreation
except:
    from fixtures import HelpObjectCreation

def main(filename):
    with open(filename) as f:
        try:
            y = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(exc)

    if not 'datadir' in y:
        y['datadir'] = Path(os.getcwd()) / y['detector']['name']
    y['datadir'] = Path(y['datadir']).resolve()
    os.makedirs(y['datadir'], exist_ok=True)

    # we must start every script with this. datadir can be left as None and RASE will initialize
    # with the last used data directory, or the cwd (if no previous directory)
    init_rase(y['datadir'])

    # Step 1: Create the detector and the associated bits (base spectra, replay tools)
    # 1a: create the replay tool first (to attach to detector)
    replay_param = y['replay']
    replay = ReplayModel(name=replay_param['name'])
    replay.set_replay_types(replay_param['type'])
    if replay_param['type'] == 'gadras_web':
        replay.drf_name = replay_param['drf_name']
    else:
        replay.exe_path = replay_param['exe_path']
        replay.settings = replay_param['settings']
        replay.n42_template_path = replay_param['n42_template_path']
        replay.input_filename_suffix = replay_param['input_filename_suffix']
    error = replay.accept()
    if error[0] is not None:
        print(error[1])
        print(error[2])

    # 1b: create the detector, load in the base spectra, attach replay tool
    detector_param = y['detector']
    bscmodel = BaseSpectraLoadModel()
    bscmodel.get_spectra_data(detector_param['base_spec_dir'])
    bscmodel.accept()  # puts the base spectra in the database
    dmodel = DetectorModel(detector_param['name'])
    dmodel.delete_relations()
    dmodel.assign_spectra(bscmodel)
    bscmodel = BaseSpectraLoadModel()
    # bscmodel.get_spectra_data(detector_param['second_bsdir'])  # required to get the calibration vals the same as
    #                                                            # experiment (important for some instruments)
    bscmodel.accept()  # puts the base spectra in the database
    dmodel.assign_spectra(bscmodel)
    dmodel.set_replay(replay_param['name'])
    # dmodel.no_secondary = no_secondary
    dmodel.detector_type_secondary = detector_param['secondary_type']
    dmodel.accept()
    detector = dmodel.detector
    print('Detector created')

    # Step 2: Create associations between base spectra names and ID results
    HelpObjectCreation().create_filled_corr_table()
    print('Correspondence table created')
    print('Running scenarios...')
    # Step 3: Create the background scenarios
    ids = []
    session = Session()
    simcontexts = None
    for bgnd in tqdm(y['backgrounds']):
        scen = ScenarioModel(data_bgnd=[list(bgnd.values())])
        scen.acq_time = y['acq_time']
        scen.replication = y['input_reps']
        scen.accept()
        bmat = Material(name=bgnd['name'], include_intrinsic=False)
        id = Scenario.scenario_hash(float(y['acq_time']), [], [
                            ScenarioBackgroundMaterial(material=bmat, dose=bgnd['value'], fd_mode=bgnd['units'])])
        scenario = session.query(Scenario).filter_by(id=id).first()
        simcontexts = [SimContext(detector, replay, scenario)]
        # Step 4b: Generate spectra
        SampleSpectraGeneration(simcontexts).work()
        # Step 4c: Run replay
        replaygen = ReplayGeneration(simcontexts)
        replaygen.runReplay()
        # Step 4d: Translate as necessary
        translation = TranslationGeneration(simcontexts)
        translation.runTranslator()
        ids.append(id)

    if not os.path.isdir(y['output_dir']):
        os.mkdir(y['output_dir'])
    if 'export_type' in y.keys():
        result_super_map, scenario_stats_df = calculateScenarioStats(simcontexts)
        if y['export_type'] in ['csv', 'both']:
            export_results(result_super_map, scenario_stats_df,
                           os.path.join(y['output_dir'], f'{detector_param["name"]}_BgndFalseID.csv'), 'csv')
        if y['export_type'] in ['json', 'both']:
            export_results(result_super_map, scenario_stats_df,
                           os.path.join(y['output_dir'], f'{detector_param["name"]}_BgndFalseID.json'), 'json')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'examples\\example_api_backgrounds.yaml'

    main(filename)