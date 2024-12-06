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
sys.path.append('../')

from pathlib import Path
import os
import yaml

sys.path.append(os.getcwd())
sys.path.append(os.getcwd()+'\\tests')

from src.rase_init import init_rase
from src.base_spectra_dialog import BaseSpectraLoadModel
from src.replay_dialog import ReplayModel
from src.detector_dialog import DetectorModel
from src.automated_s_curve import generate_curve

try:
    from tests.fixtures import HelpObjectCreation
except:
    from fixtures import HelpObjectCreation

def main(yamlpath):
    with open(yamlpath) as f:
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
    dmodel.set_replay(replay_param['name'])
    # dmodel.no_secondary = no_secondary
    dmodel.detector_type_secondary = detector_param['secondary_type']
    dmodel.accept()
    print('Detector created')

    # Step 2: Create associations between base spectra names and ID results, resetting the corr table while we're at it
    hoc = HelpObjectCreation()
    hoc.delete_corr_table('default_table')
    hoc.create_filled_corr_table()
    print('Correspondence table created')

    # Step 3: Run the S-curves
    sources = y['sources']
    bkg = y['background']
    for source in sources:
        input_basic = y['basic_scurve_params']
        input_basic['instrument'] = detector_param['name']
        input_basic['replay'] = replay_param['name']
        input_basic['source'] = source['name']
        input_basic['source_fd'] = source['units']
        input_basic['background'] = [(bkg['units'], bkg['name'], bkg['value'])]

        input_advanced = y['advanced_scurve_params']

        filename = f"{detector_param['name']}_{source['name']}_{y['basic_scurve_params']['dwell_time']}_Scurve"

        generate_curve(input_data=input_basic, advanced=input_advanced,
                       export_path=y['output_dir'],
                       custom_filename=filename,
                       export_filetype=y['export_type'])
        print(f'S-curve for source {source["name"]} completed')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        yamlpath = './examples/example_api_scurves.yaml'
        main(yamlpath)
