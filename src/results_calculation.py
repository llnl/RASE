import os
from collections import Counter
from itertools import product
import pandas as pd
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QCheckBox, QMessageBox, QProgressDialog

from src.contexts import SimContext
from src.correspondence_table_dialog import CorrespondenceData, CorrespondenceTableDialog
from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.table_def import Detector, CorrespondenceTable, CorrespondenceTableElement, \
    MaterialWeight, Scenario, Session
import traceback
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# translation_tag = 'res_c'

def calculateScenarioStats(sim_context_list: list[SimContext], gui=None):
    """
    Calculates scenario stats
    """
    session = Session()
    settings = RaseSettings()
    corrData = CorrespondenceData(gui=gui)
    corrTable = session.query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
    corrTableRows = session.query(CorrespondenceTableElement).filter_by(corr_table_name=corrTable.name)
    # add background material rows to the correspondence table
    bckg_material_set = {s for sc in sim_context_list for s in sc.scenario.get_bckg_material_names_no_shielding()}
    corr_table_iso_set = {line.isotope for line in corrTableRows}
    if gui is not None:
        for bckgMaterial in bckg_material_set:
            if bckgMaterial in corr_table_iso_set:
                continue
            print(QCoreApplication.translate('res_c', 'BCKG NOT IN CORR TABLE'))
            cb = QCheckBox(QCoreApplication.translate('res_c', 'Edit the Correspondence Table Now'))
            cb.setEnabled(True)
            msgbox = QMessageBox(QMessageBox.Question, QCoreApplication.translate('res_c',
                          '{} is currently not in Correspondence Table').format(bckgMaterial),
                         QCoreApplication.translate('res_c', 'Would you like to add {} '
                                             'to the Correspondence Table?').format(bckgMaterial))
            msgbox.addButton(QMessageBox.Yes)
            msgbox.addButton(QMessageBox.No)
            msgbox.setCheckBox(cb)
            addIsotopeToCorrTable = msgbox.exec()
            if addIsotopeToCorrTable == QMessageBox.Yes:
                corrTsbleEntry = CorrespondenceTableElement(isotope=bckgMaterial, table=corrTable,
                                                            corrList1="", corrList2="")
                corrTable.corr_table_elements.append(corrTsbleEntry)
                # if "edit correspondence" table selected
                if bool(cb.isChecked()):
                    CorrespondenceTableDialog().exec_()
    session.commit()

    sampleRootDir = settings.getSampleDirectory()
    result_super_map = {}
    columns = ['Det', 'Replay', 'Mat_Dose', 'Bkg_Mat_Dose', 'Mat_Flux', 'Bkg_Mat_Flux', 'Infl',
               'AcqTime', 'Repl',
               'Comment', 'PID', 'PID_L', 'PID_H', 'PFID', 'C&C', 'C&C_L', 'C&C_H', 'TP', 'FP',
               'FN', 'Precision', 'Recall',
               'F_Score', 'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']
    scenario_stats_df = pd.DataFrame(columns=columns)

    if gui is not None:
        progress = QProgressDialog(QCoreApplication.translate('res_c', 'Computing results...'),
                                   None, 0, len(sim_context_list) + 1, gui)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setWindowModality(Qt.WindowModal)

    for i, sc in enumerate(sim_context_list):
        if gui is not None:
            progress.setValue(i)

        scenario = sc.scenario
        scenId = scenario.id
        detector = sc.detector
        detName = detector.name
        replay = sc.replay

        res_dir = get_results_dir(sampleRootDir, detector, replay, scenId)
        if not files_exist(res_dir):
            continue

        result_super_map_key = sc
        scen_mats = scenario.get_material_names_no_shielding()
        scen_bckg_mats = scenario.get_bckg_material_names_no_shielding()

        fc_fileList = get_results_files(sampleRootDir, detector, replay, scenId)

        pid_total = 0
        pfid_total = 0
        tp_total = 0
        wtp_total = 0
        fp_total = 0
        wfp_total = 0
        fn_total = 0
        wfn_total = 0
        CandCtotal = 0
        precision_total = 0
        wprecision_total = 0
        recall_total = 0
        wrecall_total = 0
        Fscore_total = 0
        wFscore_total = 0
        num_files = 0

        result_map = {}
        isotopes, correct_ids_list, allowed_ids_list = corrData.getCorrTableData(scen_mats, scen_bckg_mats)
        assoc_table = dict(zip(isotopes, correct_ids_list))
        mats_with_weights = getMaterialWeightsData(assoc_table, settings, corrData)

        num_required_ids = len([i for i in correct_ids_list if i])
        for file in fc_fileList:
            result_list = []
            num_files = num_files + 1
            results = {}
            try:
                trans_results, trans_confidences = readTranslatedResultFile(file,
                                            settings.getUseConfidencesInCalcs(), replay)
                for r, c in zip(trans_results, trans_confidences):
                    if r in results.keys():
                        results[r] = max([results[r], c])
                    else:
                        results[r] = c
            except ResultsFileFormatException as ex:
                traceback.print_exc()
                logging.exception(QCoreApplication.translate('res_c', 'Handled Exception'), exc_info=True)
                print(QCoreApplication.translate('res_c', '{} in file {}').format(str(ex), os.path.basename(file)))
            Tp, Fn, Fp, wTp, wFn, wFp = getTpFpFn(results, allowed_ids_list, assoc_table,
                                                       mats_with_weights, corrData.corrHash)
            result_list.append(str(Tp))
            result_list.append(str(Fn))
            result_list.append(str(Fp))

            pid = 0
            pfid = 0
            precision = 0
            wprecision = 0
            recall = 0
            wrecall = 0
            Fscore = 0
            wFscore = 0
            CandC = 0

            if Tp == num_required_ids:
                pid = 1
            if Fp > 0:
                pfid = 1
            if (Tp + Fn > 0):
                recall = Tp / (Tp + Fn)
            if (Tp + Fp > 0):
                precision = Tp / (Tp + Fp)
            if (wTp + wFn > 0):
                wrecall = wTp / (wTp + wFn)
            if (wTp + wFp > 0):
                wprecision = wTp / (wTp + wFp)
            if (precision + recall > 0):
                Fscore = 2 * precision * recall / (precision + recall)
                if Fscore == 1:
                    CandC = Fscore
            if (wprecision + wrecall > 0):
                wFscore = 2 * wprecision * wrecall / (wprecision + wrecall)

            pid_total = pid_total + pid
            pfid_total += pfid
            tp_total = tp_total + Tp
            wtp_total = wtp_total + wTp
            fp_total = fp_total + Fp
            wfp_total = wfp_total + wFp
            fn_total = fn_total + Fn
            wfn_total = wfn_total + wFn
            CandCtotal = CandC + CandCtotal
            precision_total = precision_total + precision
            result_list.append(str(round(precision, 2)))
            wprecision_total = wprecision_total + wprecision
            recall_total = recall_total + recall
            result_list.append(str(round(recall, 2)))
            wrecall_total = wrecall_total + wrecall
            Fscore_total = Fscore_total + Fscore
            result_list.append(str(round(Fscore, 2)))
            wFscore_total = wFscore_total + wFscore
            result_list.append('; '.join(results))
            result_map[file] = result_list

        result_super_map[result_super_map_key] = result_map
        # FIXME: is it possible that num_files becomes zero, thus resulting in an error?
        pid_freq = pid_total / num_files
        pfid_freq = pfid_total / num_files
        (P_CI_p, P_CI_n) = calc_result_uncertainty(pid_freq, num_files)
        tp_freq = tp_total / num_files
        wtp_freq = wtp_total / num_files
        fp_freq = fp_total / num_files
        wfp_freq = wfp_total / num_files
        fn_freq = fn_total / num_files
        wfn_freq = wfn_total / num_files
        CandC_freq = CandCtotal / num_files
        (C_CI_p, C_CI_n) = calc_result_uncertainty(CandC_freq, num_files)
        precision_freq = precision_total / num_files
        wprecision_freq = wprecision_total / num_files
        recall_freq = recall_total / num_files
        wrecall_freq = wrecall_total / num_files
        Fscore_freq = Fscore_total / num_files
        wFscore_freq = wFscore_total / num_files

        mat_dose_dict = {scen_mat.material.name: scen_mat.dose for scen_mat in
                         scenario.scen_materials if
                         scen_mat.fd_mode == 'DOSE'}
        mat_dose_bkg_dict = {scen_mat.material.name: scen_mat.dose for scen_mat in
                             scenario.scen_bckg_materials if
                             scen_mat.fd_mode == 'DOSE'}
        mat_flux_dict = {scen_mat.material.name: scen_mat.dose for scen_mat in
                         scenario.scen_materials if
                         scen_mat.fd_mode == 'FLUX'}
        mat_flux_bkg_dict = {scen_mat.material.name: scen_mat.dose for scen_mat in
                             scenario.scen_bckg_materials if
                             scen_mat.fd_mode == 'FLUX'}
        scenario_stats_df.loc[result_super_map_key] = [detector.name, [replay.name if replay else None][0],
                                                        mat_dose_dict, mat_dose_bkg_dict,
                                                        mat_flux_dict, mat_flux_bkg_dict,
                                                        [infl.name for infl in scenario.influences],
                                                        scenario.acq_time, scenario.replication,
                                                        scenario.comment, pid_freq, P_CI_n, P_CI_p,
                                                        pfid_freq, CandC_freq, C_CI_n, C_CI_p,
                                                        tp_freq, fp_freq, fn_freq,
                                                        precision_freq, recall_freq, Fscore_freq,
                                                        wtp_freq, wfp_freq, wfn_freq,
                                                        wprecision_freq, wrecall_freq, wFscore_freq]


    MatDose_df = scenario_stats_df['Mat_Dose'].apply(pd.Series).fillna(0)
    MatDose_df = MatDose_df.add_prefix('Dose_')
    BkgMatDose_df = scenario_stats_df['Bkg_Mat_Dose'].apply(pd.Series).fillna(0)
    BkgMatDose_df = BkgMatDose_df.add_prefix('BkgDose_')
    MatFlux_df = scenario_stats_df['Mat_Flux'].apply(pd.Series).fillna(0)
    MatFlux_df = MatFlux_df.add_prefix('Flux_')
    BkgMatFlux_df = scenario_stats_df['Bkg_Mat_Flux'].apply(pd.Series).fillna(0)
    BkgMatFlux_df = BkgMatFlux_df.add_prefix('BkgFlux_')

    dose_scen_desc = pd.concat([MatDose_df, BkgMatDose_df], axis=1).apply(lambda x:
                                                _create_scenario_desc(x), axis=1)
    flux_scen_desc = pd.concat([MatFlux_df, BkgMatFlux_df], axis=1).apply(lambda x:
                                                _create_scenario_desc(x, italics=True), axis=1)
    scenario_stats_df['Scen Desc'] = '' if flux_scen_desc.empty else dose_scen_desc.str.cat(flux_scen_desc, sep=", ")
    scenario_stats_df = pd.concat([scenario_stats_df[['Det', 'Replay']],
                                        MatDose_df, BkgMatDose_df, MatFlux_df, BkgMatFlux_df,
                                        scenario_stats_df.loc[:, 'Infl':]], axis=1)
    if gui is not None:
        progress.setValue(len(sim_context_list) + 1)
    return result_super_map, scenario_stats_df


def getTpFpFn(results, allowed_list, assoc_table, mats_with_weights, corrHash):
    """
    calculates True Positives, False Positives, False Negatives
    :return: True Positives, False Positives, False Negatives
    """
    iso_id_required = 0
    result_keys = set(results.keys())
    FP_candidates = result_keys
    found_isotopes = {}
    not_found = {}
    Tp = 0
    wTp = 0

    for material, correct_ids in assoc_table.items():
        # if the correct_id list for this isotope is empty,
        # then we interpret it as if this isotope does not need to be identified
        if correct_ids:
            iso_id_required += 1
        # check if any of the correct IDs are within the ID results
        found = [r for r in result_keys if r in correct_ids]
        confidences = [results[key] for key in found]
        weights = mats_with_weights[material]
        if found:
            found_isotopes[material] = tuple([w * max(confidences) for w in weights])
            wTp += found_isotopes[material][0]
            Tp += 1
        # if the correspondence table row is blank or has allowed isotopes
        elif assoc_table[material] and not [r for r in result_keys if r in allowed_list]:
            not_found[material] = weights
        # whatever was not found is a potential false positive
        FP_candidates = list(set(FP_candidates) - set(found))
    for key in not_found.keys():
        if key in found_isotopes.keys():
            not_found[key].pop()

    # Now remove the allowed isotopes from the false positive candidates
    FP_list = [iso for iso in FP_candidates if iso not in allowed_list]
    # now compute Fn, Fp
    Fn = 0
    wFn = 0
    if not_found:
        wFn = sum([weight[2] for weight in not_found.values()])
        Fn = len(not_found)
    Fp = 0
    wFp = 0
    weights = None
    for id_iso in FP_list:
        for mat, [correct, _] in corrHash.items():
            if id_iso in correct:
                if weights is not None:
                    weights = tuple([max(a, b) for a, b in zip(weights, mats_with_weights[mat])])
                else:
                    weights = mats_with_weights[mat]
        if weights is not None:
            wFp += weights[1] * results[id_iso]
            Fp += 1
        else:
            wFp += 1
            Fp += 1

    return Tp, Fn, Fp, wTp, wFn, wFp


def getMaterialWeightsData(assoc_table, settings, corrData):
    session = Session()
    mat_weights = {}
    for mat in list(session.query(MaterialWeight).all()):
        mat_weights[mat.name] = (mat.TPWF, mat.FPWF, mat.FNWF)
    for key in corrData.getCorrHash().keys() | assoc_table.keys():
        if (key not in mat_weights) or not (settings.getUseMWeightsInCalcs()):
            mat_weights[key] = (1, 1, 1)
    return mat_weights


def compute_freq_results(result_super_map, sim_context_list: list[SimContext]):
    """
    Compute sorted frequency of all identification result strings for the given list of `scenario*detector` keys
    """
    freq_result_dict = {}
    if sim_context_list:
        result_strings = []
        num_entries = 0
        for sc in sim_context_list:
            if sc in result_super_map:
                result_map = result_super_map[sc]
                key_result_strings = [(x.strip() if x else "No ID") for res in result_map.values()
                                      for x in res[-1].split(';')]
                result_strings += key_result_strings
                num_entries += len(result_map)
        if num_entries:
            result_string_counter = Counter(result_strings)
            freq_result_dict = {k: f'{v / num_entries:.4g}' for k, v in sorted(result_string_counter.items(),
                                                                               key=lambda item: item[1], reverse=True)}
    return freq_result_dict


def export_results(result_super_map, scenario_stats_df, file_path: str | os.PathLike, file_type='csv'):
    """
    Exports Results Dataframe to csv or json formats. Includes ID Frequencies and detailed ID results
    """

    file_path = Path(file_path)
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    df = scenario_stats_df.copy()
    df['Scen Desc'] = df['Scen Desc'].apply(lambda x: re.sub('<[^<]+?>', '', x))
    df['ID Frequencies'] = [compute_freq_results(result_super_map, [scen_det_key, ]) for scen_det_key in df.index]
    df['ID Results'] = [(lambda k: {Path(key).name: value[-1]
                                    for (key, value) in result_super_map[k].items()})(scen_det_key)
                        for scen_det_key in df.index]

    if file_type == 'csv':
        df.to_csv(file_path)
    elif file_type == 'json':
        df.to_json(file_path, orient='index', indent=4)
    else:
        print('File type must be either "json" or "csv"')


def _create_scenario_desc(row, italics=False):
    desc = []
    for k, v in row.items():
        if v > 0:
            k = k.split('_')
            k = "".join(k[1:])
            if italics:
                desc.append(f'<em>{k}({v:.3g})</em>')
            else:
                desc.append(f'{k}({v:.3g})')
    return ', '.join(desc)
