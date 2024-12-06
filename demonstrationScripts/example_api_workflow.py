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
from pathlib import Path
import numpy as np
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.rase_init import init_rase
from src.base_spectra_dialog import BaseSpectraLoadModel
from src.contexts import SimContext
from src.replay_dialog import ReplayModel
from src.detector_dialog import DetectorModel
from src.scenario_dialog import ScenarioModel
from src.spectra_generation import SampleSpectraGeneration
from src.replay_generation import ReplayGeneration, TranslationGeneration
from src.table_def import Session, Scenario
from src.automated_s_curve import generate_curve
from tests.fixtures import HelpObjectCreation


def detector_parameters():
    """
    A utility function containing all the default paths, names, etc., to create a detector
    @return:
    """
    basespec_dir = Path(__file__).parent / '../baseSpectra/genericNaI'
    detector_name = 'dummy'
    replay_name = 'dummy_webid'
    secondary_type = 'scenario'

    return basespec_dir, detector_name, replay_name, secondary_type


def replay_parameters():
    """
    A utility function containing all the default paths, names, etc., to create a replay.
    Because we are using webID, not all the parameters are necessary. If you are using a
    standalone replay, you'll need to set some other parameters (n42 template, executable path,
    etc). For a list of all settable paramters, check ReplayModel().settable_attributes
    @return:
    """
    replay_name = 'dummy_webid'
    replay_type = 'gadras_web'
    drf_name = '1x1/NaI Front'

    return replay_name, replay_type, drf_name


def scenario_parameters():
    """
    A utility function containing all the info needed to build a scenario with two sources.
    Note that the sources must exist in the database and attached to the instrument at workflow
    runtime, otherwise RASE won't work!
    @return:
    """
    sources = [['DOSE', 'Cs137', '0.20101'], ['DOSE', 'Co60', '0.30101']]
    backgrounds = [['DOSE', 'Bgnd', '0.08']]
    comment = "easy to find"
    return sources, backgrounds, comment


def auto_s_parameters():
    """
    A utility function containing all the default auto S-curve parameters.
    These can all be set freely, though some things are required to be defined
    in the database in advance. These are:

        -input_inst: must name an existing detector
        -input_replay: must name an existing replay
        -input_source: must be a source in the base spectra of the named detector
        -source_units: must correspond to the units of the input_source
        -static_background [OPTIONAL]: list of any number of 3-element tuples with
            the structure (<units>, <source_name>, <intensity>). Source name and units
            must agree with a base spectrum associated with the named detector.

    The rest of the parameters can be set to anything, provided they maintain the type
    of these default settings.

    export_path is entirely optional, but will output a .csv file with the name <filename> (if
    filename is defined, otherwise it will define its own default filename) at the specified
    location.
    """
    # basic inputs, screen no. 1
    input_inst = 'dummy'
    input_replay = 'dummy_webid'
    input_source = 'Cs137'
    source_units = 'DOSE'
    static_background = [('DOSE', 'Bgnd', 0.08)]
    dwell_time = 60
    results_type = 'PID'
    input_repetitions = 50
    invert_curve = False

    # advanced inputs, screen no. 2
    min_init_g = 1E-8
    max_init_g = 1E-3
    points_on_edge = 5
    init_repetitions = 10
    end_points = 3
    add_points = ''
    custom_name = '[Default]'
    cleanup = True
    num_points = 6
    lower_bound = 0.1
    upper_bound = 0.9

    input_basic = {"instrument": input_inst,
               "replay": input_replay,
               "source": input_source,
               "source_fd": source_units,
               "background": static_background,
               "dwell_time": dwell_time,
               "results_type": results_type,
               "input_reps": input_repetitions,
               "invert_curve": invert_curve
               }

    input_advanced = {"min_guess": min_init_g,
                      "max_guess": max_init_g,
                      "rise_points": points_on_edge,
                      "end_points": end_points,
                      "repetitions": init_repetitions,
                      "add_points": add_points,
                      "cleanup": cleanup,
                      "custom_name": custom_name,
                      "num_points": num_points,
                      "lower_bound": lower_bound,
                      "upper_bound": upper_bound
                      }

    export_path = './api_workflow_example'
    filename = 'example_scurve.csv'

    return (input_basic, input_advanced, export_path, filename)


def create_replay(replay_name, replay_type, drf_name):
    """
    Create the replay to attach to the detector
    @param replay_name: string, must be unique
    @param replay_type: string, either 'standalone' or 'gadras_webid'
    @param drf_name: string, from drf list at fullspec website 'https://full-spectrum.sandia.gov/'
    @return: ReplayModel() (which inherits from Replay())
    """
    replay = ReplayModel(name=replay_name)
    replay.set_replay_types(replay_type)
    replay.drf_name = drf_name
    error = replay.accept()
    if error[0] is not None:
        print(error[1])
        print(error[2])
    return replay


def create_detector(base_spec_dir, detector_name, replay_name, secondary_type):
    """
    Build the detector based on base spectra, detector name, and replay tool
    Note you can build a detector without the replay tool (to just create sample spectra),
    and you can also build the detector without base spectra (though that won't do you any good...)
    @param base_spec_dir: string, path to base spectra
    @param detector_name: string, must be unique
    @param replay_name: string, replay tool must already exist
    @param secondary_type: string, either 'base_spec', 'scenario', or 'file'
            -Note that if you choose 'base_spec', you should also specify the name of the isotope
            you are interested in having as the secondary via dmodel.base_secondary =
            <base_spectrum_name>. RASE will attempt to identify a background spectrum by default if
            you do not specify anything.
            -By default, RASE will keep the livetime of the secondary spectrum (regardless of if
            it comes from a chosen base spectrum, a scenario, or a file), but will apply poisson
            sampling to it for each sample spectrum. The livetime of these secondaries can be
            changed using the command dmodel.set_bgnd_spec_dwell(<any_float>). If you don't want
            the secondary sampled at all, use the command dmodel.set_bgnd_spec_resample(False).
            -Note that if you don't want a secondary spectrum, you can simply set
            dmodel.no_secondary = True
    @return: Detector()
    """
    bscmodel = BaseSpectraLoadModel()
    bscmodel.get_spectra_data(base_spec_dir)
    bscmodel.accept()  # puts the base spectra in the database

    dmodel = DetectorModel(detector_name)
    dmodel.delete_relations()
    dmodel.assign_spectra(bscmodel)
    dmodel.set_replay(replay_name)
    dmodel.detector_type_secondary = secondary_type
    dmodel.accept()
    return dmodel.detector


def create_scenario(sources, backgrounds, comment):
    """
    Build the scenario and put it in the database
    @param sources: list of any number of 3-element tuples with the structure
                    (<units>, <source_name>, <intensity>)
    @param backgrounds: Same as sources
    @param comment: string, OPTIONAL, used here to make it easy to find later
    @return:
    """
    scen = ScenarioModel(data_src=np.array(sources), data_bgnd=np.array(backgrounds))
    scen.comment = comment
    scen.accept()


def create_correspondence_table():
    hoc = HelpObjectCreation()
    hoc.create_default_corr_table()


def run_autoscurve(input_basic, input_advanced, export_path=None, filename=None):
    """
    Generates an S-curve and exports the results to a file (if export_path is set)
    @param input_basic: dictionary, basic S-curve input values
    @param input_advanced: dictionary, advanced S-curve input values
    @param export_path: string, path to directory location
    @param filename: string, filename and extension (.csv)
    @return:
    """
    generate_curve(input_data=input_basic, advanced=input_advanced, export_path=export_path,
                   custom_filename=filename)


def main(datadir=None):

    if not datadir:
        datadir = f"{Path(__file__).parent / '../demonstration'}"
        os.makedirs(datadir, exist_ok=True)

    # we must start every script with this. datadir can be left as None and RASE will initialize
    # with the last used data directory, or the cwd (if no previous directory)
    init_rase(datadir)

    # Step 1: Create the detector and the associated bits (base spectra, replay tools)
    # 1a: create the replay tool first (to attach to detector)
    replay_args = replay_parameters()
    replay = create_replay(*replay_args)
    print('Step 1a complete')
    # 1b: create the detector, load in the base spectra, attach replay tool
    detector_args = detector_parameters()
    detector = create_detector(*detector_args)
    print('Step 1b complete')
    print('Step 1 complete, detector created')

    # Step 2: Create a scenario we would like to run
    scenario_args = scenario_parameters()
    create_scenario(*scenario_args)
    print('Step 2 complete, scenario created')

    # Step 3: Create associations between base spectra names and ID results
    create_correspondence_table()
    print('Step 3 complete, correspondence table created')

    # Step 4: Run the scenarios
    # Step 4a: Get a list of scenarios
    session = Session()
    scenario = session.query(Scenario).filter_by(comment=scenario_args[2]).first()
    print('Step 4a complete, scenarios selected')
    # Step 4b: Generate spectra
    simcontext = SimContext(detector, replay, scenario)
    SampleSpectraGeneration([simcontext]).work()
    print('Step 4b complete, sample spectra generated')
    # Step 4c: Run replay
    replay = ReplayGeneration([simcontext])
    replay.runReplay()
    print('Step 4c complete, replay tool run')
    # Step 4d: Translate as necessary
    translation = TranslationGeneration([simcontext])
    translation.runTranslator()
    print('Step 4d complete, translator run')
    print('Step 4 complete, main workflow is done')

    # Step 5: Run an S-curve, if you'd like
    scurve_args = auto_s_parameters()
    run_autoscurve(*scurve_args)
    print('Step 5 complete, s-curve created and results exported')

if __name__ == '__main__':
    datadir = None  # provide whatever path you'd like to run this test in, as a string,
                    # or leave it blank and the script will handle it all
    main()