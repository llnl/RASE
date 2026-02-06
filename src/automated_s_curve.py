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
import glob
import numpy as np
import shutil
from tqdm import tqdm
from typing import List

from PySide6.QtCore import QCoreApplication, QSize, Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from src.contexts import SimContext
from src.correspondence_table_dialog import CorrespondenceTableDialog
from src.spectra_generation import SampleSpectraGeneration
from src.rase_functions import allowed_results_file_exts, delete_scenarios, files_endswith_exists, get_results_dir
from src.rase_settings import RaseSettings
from src.replay_generation import ReplayGeneration, TranslationGeneration
from src.results_calculation import calculateScenarioStats, export_results
from src.table_def import CorrespondenceTable, Detector, Material, Scenario, ScenarioMaterial, \
                            ScenarioBackgroundMaterial, ScenarioGroup, Session, Replay
from src.view_results_dialog import ViewResultsDialog

# translation tag = 'auto_s'

def generate_curve(input_data, advanced,
                   gui=None,
                   export_path=None,
                   custom_filename=None,
                   export_filetype='both'
                   ) -> List[SimContext]:
    """
    Primary function where the points that make up the S-curve are determined
    input_data: dict, see main or docs for sample format
    advanced: dict, see main or docs for sample format
    gui: automatically passes GUI if running in GUI mode
    export_path: str, custom path to export as csv or json
    export_filetype: str, set to "csv", "json", or "both"

    returns: list of sim_contexts created by this process
    """
    session = Session()
    input_data = input_data.copy()
    advanced = advanced.copy()

    # optional arguments
    defaults = {'source_intensity': None, 'shield_material': '', 'curve_type': 0,  'shield_thickness': 0}
    for k, v in defaults.items():
        input_data.setdefault(k, v)

    if advanced['custom_name'] == QCoreApplication.translate('auto_s', '[Default]'):
        if input_data['curve_type'] == 0:
            group_name = (QCoreApplication.translate('auto_s', 'AutoScurve_{}_{}{}{}').format(
                    input_data['instrument'], input_data['source'],
                    '_{}'.format(input_data['shield_material']) if input_data['shield_thickness'] else '',
                    '={}cm'.format(input_data['shield_thickness']) if input_data['shield_thickness'] else ''))
        else:
            group_name = (QCoreApplication.translate('auto_s', 'AutoScurve_{}_{}_{}={}{}').format(
                        input_data['instrument'], input_data['shield_material'],
                        input_data['source'], input_data['source_intensity'],
                        '\u00B5Sv/h' if input_data['source_fd']=='DOSE' else '\u03B3/(cm\u00B2s)'))
    else:
        suffix = 0
        while True:
            if session.query(ScenarioGroup).filter_by(name=advanced['custom_name']).first():
                if not session.query(ScenarioGroup).filter_by(name=advanced['custom_name']).first().scenarios:
                    group_name = (advanced['custom_name'])
                    break
                else:
                    suffix += 1
                    advanced['custom_name'] = advanced['custom_name'] + '_' + str(suffix)
            else:
                group_name = (advanced['custom_name'])
                break

    detName = [input_data['instrument']]
    detector = session.query(Detector).filter_by(name=detName[0]).first()
    repName = [input_data['replay']]
    replay = session.query(Replay).filter_by(name=repName[0]).first()
    condition = False
    already_done = False

    expand = 0
    first_run = True
    # All scenarios within the group that have the same source/backgrounds
    make_scen_group(session, group_name, input_data)
    scenIdall = make_scenIdall(session, input_data)
    # scenarios that will be rerun in this run
    scenIds_no_persist = []
    additional_points = None
    # sim_context_all = [SimContext(detector=detector, replay=replay, scenario=session.query(Scenario).filter_by(id=s).first()) for s in scenIdall]

    maxback = 0
    if input_data['background']:
        for bmat in input_data['background']:
            bmat = bmat[0]
            if bmat[0] == input_data['source_fd']:
                if maxback == 0:
                    maxback = float(bmat[2])
                else:
                    maxback = max(maxback, float(bmat[2]))
    if not maxback:
        maxback = 0.1

    nabove = 1
    nbelow = 1
    edges = False
    edge_points = []
    while not condition:
        # newly generated scenIds, and all scenIds with source/backgrounds as defined in the auto s-curve gui
        scenIds, scenIds_no_persist, scenIdall = gen_scens(input_data, advanced, session, scenIdall, scenIds_no_persist,
                                       group_name, advanced['repetitions'], condition, additional_points, edge_points)

        try:
            abort = run_scenarios(scenIds, detector, replay, condition, expand, first_run, gui, edges=edges,
                                  curve_type=input_data['curve_type'], source_fd=input_data['source_fd'])
        except KeyboardInterrupt:
            abort = True
        first_run = False
        if abort:
            cleanup_scenarios(advanced['repetitions'], scenIds_no_persist)
            return []

        sim_context_all = [SimContext(detector=detector, replay=replay,
                                      scenario=session.query(Scenario).filter_by(id=s).first()) for s in scenIdall]
        result_super_map, scenario_stats_df = calculateScenarioStats(sim_context_all, gui)

        if input_data['results_type'] in ['C&C', 'TP', QCoreApplication.translate('auto_s', 'Precision'), QCoreApplication.translate('auto_s', 'Recall')]:
            results = scenario_stats_df[input_data['results_type']]
        elif input_data['results_type'] == QCoreApplication.translate('auto_s', 'Fscore'):
            results = scenario_stats_df['F_Score']
        else:  # to add more later
            results = scenario_stats_df['PID']
        results = results.sort_values(ascending=(not input_data['invert_curve']))

        if max(results) >= advanced['upper_bound'] and min(results) <= advanced['lower_bound']:
            """If there are values surrounding the rising edge"""
            # find scenarios in for cases
            ids_on_edge = []
            start_list = []
            end_list = []
            prev_point = False
            for index, result in enumerate(results):
                if (not input_data['invert_curve'] and result <= advanced['lower_bound']) or \
                        (input_data['invert_curve'] and result >= advanced['upper_bound']):
                    start_list.append(results.index[index].scenario.id)
                    if prev_point:
                        ids_on_edge = []  # rose and then dropped back down (i.e.: fluctuations)
                        prev_point = False
                if advanced['lower_bound'] <= result <= advanced['upper_bound']:
                    ids_on_edge.append(results.index[index].scenario.id)
                    prev_point = True
                if (not input_data['invert_curve'] and result >= advanced['upper_bound']) or \
                        (input_data['invert_curve'] and result <= advanced['lower_bound']):
                    end_list.append(results.index[index].scenario.id)
            # Grab doses for scenarios on the edges of the S-curve. The first value in each list is
            # the value that is the second closest to the rising edge, and the second is the closest
            start_val = [1e-8, 1e-8]
            end_val = [1e-3, 1e-3]

            # refines the start_val and end_val values based on the start and end lists
            for startendvallist, scenlist, reversed in zip([start_val, end_val], [start_list, end_list], [False, True]):
                if input_data['curve_type'] == 0:
                    doseorthicklist = [session.query(Scenario).filter_by(id=s).first().scen_materials[0].dose for s in scenlist]
                else:
                    doseorthicklist = [session.query(Scenario).filter_by(id=s).first().shielding_thickness for s in scenlist]
                if not len(doseorthicklist):
                    continue
                elif len(doseorthicklist) == 1:
                    startendvallist[0:] = [doseorthicklist[0], doseorthicklist[0]]
                else:
                    startendvallist[0:] = sorted(doseorthicklist, reverse=reversed)[-2:]

            # check if there are enough points on the rising edge
            if len(ids_on_edge) >= advanced['rise_points'] and len(end_list) > advanced['end_points'] and len(
                                                                                start_list) > advanced['end_points']:
                condition = True
                # to avoid persistence errors by reusing a value with the same ID but different replications
                edge_count, bound_scens_start, bound_scens_end = check_edge_ids(session, input_data[
                                                                    'input_reps'], start_list,
                                                                    end_list, ids_on_edge, detector, replay)
                if edge_count < advanced['rise_points'] or bound_scens_start < advanced['end_points'] or \
                        bound_scens_end < advanced['end_points']:  # set the bounds for the high statistics S-curve
                    advanced['min_guess'] = start_val[1]
                    advanced['max_guess'] = end_val[1]
                    advanced['num_points'] = advanced['rise_points']
                    if advanced['add_points'] == []:
                        additional_points = None
                    else:
                        try:
                            additional_points = [float(k) for k in advanced['add_points'].split(',')]
                        except:
                            print('Could not add user-specified points, ignoring these points and continuing') # TODO: logger
                            additional_points = None
                    edge_points = logspace_gen(advanced['end_points'],
                                               start_val[0] / max(nbelow, advanced['end_points']), start_val[0]) + \
                                  logspace_gen(advanced['end_points'],
                                               end_val[0], end_val[0] * max(nabove,advanced['end_points']))
                else:
                    already_done = True
                edges = False
            else:
                # avoid infinite loop due to being stuck on edge cases. Moves slightly inward to better populate edge
                if len(ids_on_edge) < advanced['rise_points']:
                    if start_val[1] == advanced['min_guess']:
                        advanced['min_guess'] = start_val[1] + (end_val[1] - start_val[1]) * 0.01 * np.random.normal(1, 0.1)
                    else:
                        advanced['min_guess'] = start_val[1]
                    if end_val[1] == advanced['max_guess']:
                        advanced['max_guess'] = end_val[1] - (end_val[1] - start_val[1]) * 0.01 * np.random.normal(1, 0.1)
                    else:
                        advanced['max_guess'] = end_val[1]
                    advanced['num_points'] = advanced['rise_points']  # + 4
                    edges = False
                elif len(end_list) <= advanced['end_points']:
                    advanced['min_guess'] = end_val[0] * (nabove + 0.1)
                    advanced['max_guess'] = end_val[0] * (nabove + 1)
                    advanced['num_points'] = 2  # to ensure we step through both the new points
                    nabove += 1
                    if nabove > 20:  # to prevent an infinite loop
                        fail_endpoints(scenIdall, detector, replay, gui)
                        return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                    edges = True
                else:
                    advanced['min_guess'] = start_val[0] / (nbelow + 0.1)
                    advanced['max_guess'] = start_val[0] / (nbelow + 1)
                    advanced['num_points'] = 2  # to ensure we step through both the new points
                    nbelow += 1
                    if nbelow > 20:  # to prevent an infinite loop
                        fail_endpoints(scenIdall, detector, replay, gui)
                        return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                    edges = True

        elif min(results) > advanced['lower_bound']:
            """If the quoted results aren't small enough yet"""
            expand += 1
            val_list = []
            for scenId in scenIdall:
                scen = session.query(Scenario).filter_by(id=scenId).first()
                if input_data['curve_type'] == 0:
                    val_list.append(scen.scen_materials[0].dose)
                else:
                    val_list.append(scen.shielding_thickness)
            val_list.sort()

            if not input_data['invert_curve']:
                val_bound = val_list[0]
                if (0 < val_bound <= 1E-9 * maxback and len(scenIdall) >= 9) or 0 < val_bound <= 1E-12:
                    fail_never(scenIdall, detector, replay, input_data['source'], export_path, custom_filename, gui)
                    return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                if len(val_list) > 1:
                    step_ratio = val_list[0] / val_list[1]
                else:
                    step_ratio = 1/1.5
                advanced['min_guess'] = min(val_bound, advanced['min_guess']) * step_ratio
                advanced['max_guess'] = advanced['min_guess']
                advanced['num_points'] = 2
            else:
                val_bound = val_list[-1]
                if val_bound >= 800 * maxback and len(scenIdall) >= 9:
                    fail_never(scenIdall, detector, replay, input_data['source'], export_path, custom_filename, gui)
                    return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                if len(val_list) > 1:
                    step_ratio = val_list[-1] / val_list[-2]
                else:
                    step_ratio = 1.5
                advanced['min_guess'] = max(val_bound, advanced['max_guess']) * step_ratio
                advanced['max_guess'] = advanced['min_guess']
                advanced['num_points'] = 2

        elif max(results) < advanced['upper_bound']:
            """If the quoted results aren't large enough yet"""
            expand += 1
            val_list = []
            for scenId in scenIdall:
                scen = session.query(Scenario).filter_by(id=scenId).first()
                if input_data['curve_type'] == 0:
                    val_list.append(scen.scen_materials[0].dose)
                else:
                    val_list.append(scen.shielding_thickness)
            val_list.sort()
            if not input_data['invert_curve']:
                val_bound = val_list[-1]
                if val_bound >= 800 * maxback and len(scenIdall) >= 9:
                    fail_always(scenIdall, detector, replay, input_data['source'], export_path, custom_filename, gui)
                    return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                if len(val_list) > 1:
                    step_ratio = val_list[-1] / val_list[-2]
                else:
                    step_ratio = 1.5
                advanced['min_guess'] = max(val_bound, advanced['max_guess']) * step_ratio
                advanced['max_guess'] = advanced['min_guess']
                advanced['num_points'] = 2
            else:
                val_bound = val_list[0]
                if (0 < val_bound <= 1E-9 * maxback and len(scenIdall) >= 9) or 0 < val_bound <= 1E-12:
                    fail_always(scenIdall, detector, replay, input_data['source'], export_path,
                                custom_filename, gui)
                    return [SimContext(detector, replay, session.get(Scenario, s_id)) for s_id in scenIdall]
                if len(val_list) > 1:
                    step_ratio = val_list[0] / val_list[1]
                else:
                    step_ratio = val_list[0] * 1/1.5
                advanced['min_guess'] = min(val_bound, advanced['min_guess']) * step_ratio
                advanced['max_guess'] = advanced['min_guess']
                advanced['num_points'] = 2

    if condition:
        if not already_done:
            scenIds, _, _ = gen_scens(input_data, advanced, session, scenIdall, scenIds_no_persist,
                                      group_name, input_data['input_reps'], condition, additional_points, edge_points)
            detector = session.query(Detector).filter_by(name=detName[0]).first()
            abort = run_scenarios(scenIds, detector, replay, condition, gui=gui, curve_type=input_data['curve_type'],
                                  source_fd=input_data['source_fd'])
            if abort:
                cleanup_scenarios(advanced['repetitions'], scenIds_no_persist)
                cleanup_scenarios(input_data['input_reps'], scenIds)
                return []
        else:
            scens = [session.query(Scenario).filter_by(id=scenId).first() for scenId in scenIdall]
            scenIds = [scen.id for scen in [s for s in scens if s.replication == max([k.replication for k in scens])]]

        # Final cleanup if requested by user
        if advanced['cleanup']:
            cleanup_scenarios(advanced['repetitions'], scenIds_no_persist)
            if gui is not None:
                try:
                    gui.populateScenarios()
                except:
                    raise Exception(QCoreApplication.translate('auto_s', 'RASE object not provided, cannot populate GUI '
                                                 'with scenarios.'))

        results_message = [QCoreApplication.translate('auto_s', 'S-Curve generation complete!'),
                            QCoreApplication.translate('auto_s', 'Would you like to view the results?')]
        sim_contexts = [SimContext(detector=detector, replay=replay,
                                   scenario=session.query(Scenario).filter_by(id=s).first()) for s in scenIds]

        if gui is not None:
            msgbox = QMessageBox(QMessageBox.Question, results_message[0], results_message[1])
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            answer = msgbox.exec()
            if answer == QMessageBox.Yes:
                viewResults(gui, sim_contexts)
        else:
            print(QCoreApplication.translate('auto_s', '{} Group name: {}, Scenario IDs: {}').format(results_message[0],
                                                                     group_name, ", ".join(str(k) for k in scenIds)))
            if export_path is not None:
                if not os.path.isdir(export_path):
                    os.mkdir(export_path)
                if custom_filename is None:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    dtnow = now.strftime("%Y_%m_%d__%H_%M_%S")
                    filename = QCoreApplication.translate('auto_s', 'autoscurve_{}_{}_{}'.format(input_data[
                                                                         'instrument'], input_data['source'], dtnow))
                else:
                    filename = custom_filename
                result_super_map, scenario_stats_df = calculateScenarioStats(sim_contexts)
                if export_filetype in ['csv', 'both']:
                    export_results(result_super_map, scenario_stats_df,
                                   os.path.join(export_path, filename + '.csv'), 'csv')
                if export_filetype in ['json', 'both']:
                    export_results(result_super_map, scenario_stats_df,
                                   os.path.join(export_path, filename + '.json'), 'json')

    final_scenario_ids = scenIds if advanced['cleanup'] else scenIds + scenIds_no_persist
    return [SimContext(detector=detector, replay=replay, scenario=session.get(Scenario, s_id)) for s_id in final_scenario_ids]


def check_edge_ids(session, replications, start_list, end_list, edge_ids, detector, replay):
    """Check if there are results ready for values on the rising edge of the S-curve"""
    settings = RaseSettings()
    counter = [0] * 3
    for i, ids_list in enumerate([edge_ids, start_list, end_list]):
        for id in ids_list:
            scen = session.query(Scenario).filter_by(id=id).first()
            results_dir = get_results_dir(settings.getSampleDirectory(), detector, replay, id)
            if files_endswith_exists(results_dir, allowed_results_file_exts) and scen.replication >= replications:
                counter[i] += 1

    return counter[0], counter[1], counter[2]


def fail_never(scenIdall, detector: Detector, replay: Replay, sourcename='', export_path=None, custom_filename=None, gui=False):
    """Prints/shows message box if isotopes are always ID'd"""
    out_text = [QCoreApplication.translate('auto_s', 'Convergence Issue'), QCoreApplication.translate(
                'auto_s', 'There may be some issue; the isotope identifier is always identifying '
                'some of the isotope of interest! Please take a close look at the results for '
                'trouble shooting.'), QCoreApplication.translate('auto_s', 'Would you like to '
                                               'open the results table for this scenario group?')]
    if gui is not None:
        msgbox = QMessageBox(QMessageBox.Question, out_text[0], f'{out_text[1]} {out_text[2]}')
        create_answer_box(msgbox, gui, scenIdall, detector, replay)
    else:
        print(f'{out_text[0]}: {out_text[1]}')
    if export_path is not None:
        if not os.path.isdir(export_path):
            os.mkdir(export_path)
        if custom_filename is None:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            dtnow = now.strftime("%Y_%m_%d__%H_%M_%S")
            filename = QCoreApplication.translate('auto_s', 'autoscurve_{}_{}_{}'.format(detector.name, sourcename, dtnow))
        else:
            filename = custom_filename
        with open(os.path.join(export_path, filename + '_failnever.txt'), 'w') as f:
            f.write(QCoreApplication.translate('auto_s', 'No source intensity yielded source IDs for {} below than the '
                                                         'lower ID threshold.'.format(detector.name)))
    return True


def fail_always(scenIdall, detector: Detector, replay: Replay, sourcename='', export_path=None, custom_filename=None, gui=False):
    """Prints/shows message box if no isotopes are ID'd"""
    out_text = [QCoreApplication.translate('auto_s', 'Convergence Issue'), QCoreApplication.translate(
                    'auto_s', 'There may be some issue; no isotopes are being identified at any '
                    'attempted intensity. You might want to check your correspondence table.'),
                    QCoreApplication.translate('auto_s', 'Would you like to open the results '
                                                         'table for this scenario group?')]
    if gui is not None:
        msgbox = QMessageBox(QMessageBox.Question, out_text[0], f'{out_text[1]} {out_text[2]}')
        create_answer_box(msgbox, gui, scenIdall, detector, replay)
    else:
        print(f'{out_text[0]}: {out_text[1]}')
    if export_path is not None:
        if not os.path.isdir(export_path):
            os.mkdir(export_path)
        if custom_filename is None:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            dtnow = now.strftime("%Y_%m_%d__%H_%M_%S")
            filename = QCoreApplication.translate('auto_s', 'autoscurve_{}_{}_{}'.format(detector.name, sourcename, dtnow))
        else:
            filename = custom_filename
        with open(os.path.join(export_path, filename + '_failalways.txt'), 'w') as f:
            f.write(QCoreApplication.translate('auto_s', 'No source intensity yielded source IDs for {} greater than '
                                                         'the upper ID threshold.'.format(detector.name)))
    return True

def fail_endpoints(scenIdall, detector: Detector, replay: Replay, gui):
    """Prints/shows message if we're infinitely trying to find end points"""
    out_text = ['End point issue', 'Cannot find end points to satisfy requirements automatically, '
                'possibly due to the S-curve inflecting at the ends.',
                'Would you like to open the results table for this scenario group?']
    if gui is not None:
        msgbox = QMessageBox(QMessageBox.Question, out_text[0], f'{out_text[1]} {out_text[2]}')
        create_answer_box(msgbox, gui, scenIdall, detector, replay)
    else:
        print(f'{out_text[0]}: {out_text[1]}')
    return True

def create_answer_box(msgbox, gui, scenIdall, detector: Detector, replay: Replay):
    msgbox.addButton(QMessageBox.Yes)
    msgbox.addButton(QMessageBox.No)
    answer = msgbox.exec()
    if answer == QMessageBox.Yes:
        sim_context_all = [
            SimContext(detector=detector, replay=replay,
                       scenario=Session().query(Scenario).filter_by(id=s).first()) for s in scenIdall]
        viewResults(gui, sim_context_all)


def make_scen_group(session, group_name, input_data):
    scenGroup = session.query(ScenarioGroup).filter_by(name=group_name).first()
    if not scenGroup:
        scenGroup = ScenarioGroup(name=group_name, description='')
        session.add(scenGroup)
    else:
        scenGroup.description = ''


def make_scenIdall(session, input_data):
    """
    Identify all scenarios for which results exist and that could be used as a part of this S-curve
    :param session:
    :param input_data:
    :return:
    """
    settings = RaseSettings()
    detector = session.query(Detector).filter_by(name=input_data['instrument']).first()
    replay = session.query(Replay).filter_by(name=input_data['replay']).first()

    repeat_scens = session.query(Scenario).join(ScenarioMaterial).join(
            ScenarioBackgroundMaterial).filter(
            Scenario.acq_time == float(input_data['dwell_time'])).filter(
            Scenario.shielding_material == input_data['shield_material']).filter(
            ScenarioMaterial.fd_mode == input_data['source_fd'],
            ScenarioMaterial.material_name == input_data['source'])

    if input_data['curve_type'] == 0:
        repeat_scens = repeat_scens.filter(Scenario.shielding_thickness == input_data['shield_thickness'])
    else:
        repeat_scens = repeat_scens.filter(ScenarioMaterial.dose == input_data['source_intensity'])

    input_bgnds = set(tuple([f[0], f[1], float(f[2])]) for f in input_data['background']) # ignore neutrons
    matching_scenarios = [scen for scen in repeat_scens.all() if set((b.fd_mode, b.material_name, b.dose) for
                                                                b in scen.scen_bckg_materials) == input_bgnds]

    # for s in list(repeat_scens):
    #     if len(s.scen_materials) > 1:
    #         repeat_scens.remove(s)
    #
    # common_scens = [x for x in set(repeat_scens) if repeat_scens.count(x) == len(input_data['background'])]

    scenIdall = []
    for scen in matching_scenarios:
        results_dir = get_results_dir(settings.getSampleDirectory(), detector, replay, scen.id)
        if files_endswith_exists(results_dir, allowed_results_file_exts):
            scenIdall.append(scen.id)

    return scenIdall


def gen_scens(input_data, advanced, session, scenIdall, scenIds_no_persist, group_name, reps=1, condition=False,
              additional_points=None, edge_points=None):
    """
    Generate the scenarios, including source, background, dwell time, and replications
    :param input_data: Object that contains all the basic data for the S-curve running
    :param advanced: Object that contains all the data from the "advanced" tab on the dialog
    :param session: Database session
    :param scenIdall: All scenarios that are included in the development of the S-curve
    :param scenIds_no_persist: List of scenarios to delete if the S-curve is aborted (cleanup). Distinct from
                                scenIds in that scenIds includes previously-run scenarios that can also be
                                included in the S-curve that we don't want to clear out if aborted
    :param group_name: Group we will be putting the scenarios created here
    :param reps: num replications for the scenario to be created
    :param condition: Has the S-curve converged?
    :param additional_points: User-provided points we want included in the final S-curve to matter what
    :param edge_points: Points on the edge of the S-curve
    :return:
    """
    settings = RaseSettings()
    scenGroup = session.query(ScenarioGroup).filter_by(name=group_name).first()
    test_points = logspace_gen(num_points=advanced['num_points'],
                               start_g=advanced['min_guess'], end_g=advanced['max_guess'])
    m = session.query(Material).filter_by(name=input_data['source']).first()
    scenIds = []  # scenarios that would be generated here regardless of persistence to prevent accidental duplicates

    if additional_points is not None and condition:
        try:
            test_points += additional_points  # more points to high-stats run
        except:
            print(QCoreApplication.translate('auto_s', 'Could not add user-specified points, ignoring these points '
                                                       'and continuing.'))
    if edge_points is not None:
        test_points += edge_points

    for tp in set(test_points):
        if input_data['curve_type'] == 0: # variable dose
            sm = ScenarioMaterial(material=m, fd_mode=input_data['source_fd'], dose=tp)
            shield_thick = input_data['shield_thickness']
        else: # variable shielding
            sm = ScenarioMaterial(material=m, fd_mode=input_data['source_fd'], dose=input_data['source_intensity'])
            shield_thick = tp
        sb = []
        for mode, mat, dose, *n_dose in input_data['background']:   # backward
            bm = session.query(Material).filter_by(name=mat).first()
            n_dose = 0 if not n_dose or (n_dose and not n_dose[0]) else n_dose[0]
            sb.append(ScenarioBackgroundMaterial(material=bm, fd_mode=mode, dose=float(dose), neutron_dose=n_dose))
        # check if the scenario already exists in the database. If so, and replications are >= requested, include it
        # in the S-curve, but make sure you don't delete it if S-curve is aborted
        scen_preexisting = session.query(Scenario).filter_by(id=Scenario.scenario_hash(input_data['dwell_time'],
                                                           [sm], sb, [], input_data['shield_material'],
                                                                                       shield_thick)).first()
        if scen_preexisting:
            if scen_preexisting.replication < reps:
                # Delete the scenario so it can be recreated
                delete_scenarios([scen_preexisting.id,], settings.getSampleDirectory())

                folders = [fd for fd in glob.glob(os.path.join(settings.getSampleDirectory(), '*' + scen_preexisting.id + '*'))]
                for folder in folders:
                    shutil.rmtree(folder)

                sm = ScenarioMaterial(material=m, fd_mode=input_data['source_fd'],
                                      dose=tp if input_data['curve_type'] == 0 else input_data['source_intensity'])
                define_and_add_scens(session, scenIds, scenIds_no_persist, scenGroup, input_data['dwell_time'],
                                     reps, [sm], sb, input_data['shield_material'], shield_thick)
            else:
                scenIds.append(scen_preexisting.id)
        else:
            define_and_add_scens(session, scenIds, scenIds_no_persist, scenGroup, input_data['dwell_time'],
                                 reps, [sm], sb, input_data['shield_material'], shield_thick)

    scenIdall = scenIdall + [s for s in scenIds if not s in scenIdall]
    session.commit()
    return scenIds, scenIds_no_persist, scenIdall

def define_and_add_scens(session, scenIds, scenIds_no_persist, scenGroup, dwell, reps, mats, bgnds, shmat, shthick):
    """Utility function supporting gen_scens"""
    scens = Scenario(dwell, reps, mats, bgnds, [], [], shmat, shthick)
    session.add(scens)
    scenIds.append(scens.id)
    scenIds_no_persist.append(scens.id)
    scenGroup.scenarios.append(scens)

def run_scenarios(scenIds, detector, replay, condition=False, expand=0, first_run=False, gui=None, edges=False,
                  curve_type=0, source_fd='Dose'):
    """Runs the RASE workflow functions"""
    if not len(scenIds):
        return
    settings = RaseSettings()
    count = 0
    len_prog = len(scenIds)
    session = Session()
    if curve_type == 0:
        doses = [session.query(Scenario).filter_by(id=s).first().scen_materials[0].dose for s in scenIds]
    else:
        material = session.query(Scenario).filter_by(id=scenIds[0]).first().shielding_material
        thicknesses = [session.query(Scenario).filter_by(id=s).first().shielding_thickness for s in scenIds]
    if condition:
        message = [QCoreApplication.translate('auto_s', 'S-curve range found!'),
                   QCoreApplication.translate('auto_s', 'Generating higher statistics scenarios...')]
    else:
        if len(scenIds) == 1:
            len_prog = 3
            if curve_type == 0:
                outstring = QCoreApplication.translate('auto_s', 'Steps taken = {}, Scenario ID = {}, '
                             'looking at {}={}').format(str(expand - 1), scenIds[0], source_fd, doses[0])
            else:
                outstring = QCoreApplication.translate('auto_s', 'Steps taken = {}, Scenario ID = {}, '
                             'looking at {}={}cm').format(str(expand - 1), scenIds[0], material, thicknesses[0])
            message = [QCoreApplication.translate('auto_s', 'Expanding S-curve search...'), outstring]
        else:
            if curve_type == 0:
                outstring = QCoreApplication.translate('auto_s', 'Looking at {}={}').format(
                    source_fd, ', '.join(f'{k:.3f}' for k in doses))
            else:
                outstring = QCoreApplication.translate('auto_s', 'Looking at {}=({})cm').format(
                    material, ', '.join(f'{k:.3f}' for k in thicknesses))
            if first_run:
                message = [QCoreApplication.translate('auto_s', 'Generating range-finding S-curve scenarios...'),
                           outstring]
            elif edges:
                message = [QCoreApplication.translate('auto_s', 'Adding points on the edges...'), outstring]
            else:
                message = [QCoreApplication.translate('auto_s', 'Adding scenarios to rising edge...'), outstring]

    print(f'{message[0]} {message[1]}')
    if gui is not None:
        progress = QProgressDialog(f'{message[0]}\n{message[1]}', QCoreApplication.translate('auto_s', 'Abort'), 0, len_prog, gui)
        progress.setMaximum(len_prog)
        progress.setMinimumDuration(0)
        progress.setValue(count)
        progress.resize(QSize(300, 50))
        progress.setWindowModality(Qt.WindowModal)

    try:
        if gui is not None:
            iterable = scenIds
        else:
            iterable = tqdm(scenIds)
        for scenId in iterable:
            if gui is not None and progress.wasCanceled():
                progress.close()
                return True
            scenario = Session().query(Scenario).filter_by(id=scenId).first()
            results_dir = get_results_dir(settings.getSampleDirectory(), detector, replay, scenId)
            sc = SimContext(detector, replay, scenario)
            # do not regenerate already existing results
            # using scenIds instead of scenIds_no_persist in case the scenario exists but with no results
            if not files_endswith_exists(results_dir, allowed_results_file_exts):
                SampleSpectraGeneration([sc]).work()
                if gui is not None and len(scenIds) == 1:
                    count += 1
                    progress.setValue(count)
                ReplayGeneration([sc]).runReplay()
                if gui is not None and len(scenIds) == 1:
                    count += 1
                    progress.setValue(count)
                TranslationGeneration([sc]).runTranslator()
            count += 1
            if gui is not None:
                progress.setValue(count)
        if gui is not None:
            progress.setValue(len_prog)
    except KeyboardInterrupt:
        return True


def logspace_gen(num_points=6, start_g=1E-5, end_g=1.):
    """Generates a uniformly spaced list of points"""
    end_g = 1E-10 if end_g < 1E-10 else end_g
    start_g = 1E-12 if start_g < 1E-12 else start_g
    test_points = np.geomspace(start_g, end_g, num_points)
    return [float('{:9.12f}'.format(i)) for i in test_points]


def set_bounds(val, dose):
    if val[0] == -1:
        val[0] = dose
    else:
        val[0] = val[1]
    val[1] = dose
    return val


def cleanup_scenarios(rangefind_rep, scenIds: List[str]):
    """Remove scenarios from the database that were rangefinders, i.e.: low replication scenarios"""
    settings = RaseSettings()
    scenarios = Session().query(Scenario).filter(Scenario.id.in_(scenIds)).all()
    scens_to_delete = [s.id for s in scenarios if s.replication == rangefind_rep]
    delete_scenarios(scens_to_delete, settings.getSampleDirectory())


def viewResults(gui, sim_context_list: list[SimContext]):
    """
    Opens Results table
    """
    # need a correspondence table in order to display results!
    session = Session()
    settings = RaseSettings()
    default_corr_table = session.query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
    if not default_corr_table:
        msgbox = QMessageBox(QMessageBox.Question, QCoreApplication.translate('auto_s', 'No Correspondence Table set!'),
                             QCoreApplication.translate('auto_s', 'No correspondence table set! Would you like to set a '
                                'correspondence table now?'))
        msgbox.addButton(QMessageBox.Yes)
        msgbox.addButton(QMessageBox.No)
        answer = msgbox.exec()
        if answer == QMessageBox.Yes:
            CorrespondenceTableDialog().exec_()
            settings.setIsAfterCorrespondenceTableCall(True)
        else:
            return
    gui.result_super_map, gui.scenario_stats_df = calculateScenarioStats(sim_context_list, gui)
    d = ViewResultsDialog(gui, sim_context_list)
    d.setModal(True)
    d.exec()


if __name__ == "__main__":
    from src.rase_init import init_rase

    init_rase()

    input_inst = 'dummy'
    input_replay = 'dummy_webid'
    curve_type = 0
    results_type = 'PID'
    invert_curve = False
    input_source = 'Cd109'
    source_units = 'FLUX'
    source_intensity = None
    shield_material = ''
    shield_thickness = 0
    static_background = [('DOSE', 'Bgnd', 0.08)]
    dwell_time = 30
    input_repetitions = 50

    min_init_g = 1E-8
    max_init_g = 1E-3
    points_on_edge = 5
    init_repetitions = 10
    add_points = ''
    custom_name = QCoreApplication.translate('auto_s', '[Default]')
    cleanup = True
    num_points = 6
    lower_bound = 0.1
    upper_bound = 0.9

    input_d = {'instrument': input_inst,
               'replay': input_replay,
               'curve_type': curve_type,
               'results_type': results_type,
               'invert_curve': invert_curve,
               'source': input_source,
               'source_fd': source_units,
               'source_intensity': source_intensity,
               'shield_material': shield_material,
               'shield_thickness': shield_thickness,
               'background': static_background,
               'dwell_time': dwell_time,
               'input_reps': input_repetitions,
               }

    input_advanced = {'min_guess': min_init_g,
                      'max_guess': max_init_g,
                      'rise_points': points_on_edge,
                      'repetitions': init_repetitions,
                      'add_points': add_points,
                      'cleanup': cleanup,
                      'custom_name': custom_name,
                      'num_points': num_points,
                      'lower_bound': lower_bound,
                      'upper_bound': upper_bound
                      }

    export_path = './scurve_output'

    generate_curve(input_data=input_d, advanced=input_advanced, export_path=export_path)
    print(QCoreApplication.translate('auto_s', 'Complete!'))
