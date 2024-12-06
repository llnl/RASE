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
from time import sleep

import pytest
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QDialogButtonBox, QMenu, QApplication, QMessageBox, QDialog

from src.correspondence_table_dialog import CorrespondenceTableDialog as ctd
from src.detector_dialog import DetectorDialog, DetectorModel
from src.replay_dialog import ReplayModel
from src.rase import Rase, SampleSpectraGenerationGUI, ReplayGenerationGUI
from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.results_calculation import calculateScenarioStats
from src.scenario_group_dialog import GroupSettings as gsd
from src.table_def import ScenarioGroup, Replay, CorrespondenceTable, BackgroundSpectrum
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.orm.session import _sessions
from src.spectra_generation import SampleSpectraGeneration
from src.replay_generation import ReplayGeneration
from src.replay_dialog import ReplayDialog
# from src.create_shielded_spectra_dialog import ShieldingModule
# pytest.main(['-s'])
from .fixtures import (temp_data_dir, db_and_output_folder, generic_nai_spectra, dummy_base_spectrum,
                       HelpObjectCreation, Helper)
from itertools import product


# Database testing
class Test_Database:
    def test_set_db_loc(self):
        """
        Verifies that the database location can be set
        """
        import os
        data_dir = os.getcwd()
        settings = RaseSettings()
        settings.setDataDirectory(data_dir)
        assert data_dir == settings.getDataDirectory()


    def test_database(self):
        """
        Make sure Database exists
        """
        session = Session()
        assert session


# GUI testing
class Test_GUI:
    def test_gui(self, qtbot):
        """
        Verifies the GUI is visible and key buttons are enabled
        """
        w = Rase([])
        w.show()
        qtbot.addWidget(w)
        qtbot.waitExposed(w)
        sleep(.25)

        def close_d_dialog():
            qtbot.mouseClick(w.d_dialog.buttonBox.button(QDialogButtonBox.Cancel), Qt.LeftButton)

        QTimer.singleShot(500, close_d_dialog)
        qtbot.mouseClick(w.btnAddDetector, Qt.LeftButton)

        assert w.isVisible()
        assert w.btnAddDetector.isEnabled()
        assert w.btnAddScenario.isEnabled()
        assert w.menuFile.isEnabled()
        assert w.menuTools.isEnabled()
        assert w.menuTools_2.isEnabled()
        assert w.menuHelp.isEnabled()


    def test_detector_dialog_opens(self, qtbot):
        """
        Can we open and close the detector dialog?
        """
        w = Rase([])
        w.show()
        qtbot.addWidget(w)

        def close_d_dialog():
            assert w.d_dialog
            qtbot.mouseClick(w.d_dialog.buttonBox.button(QDialogButtonBox.Cancel), Qt.LeftButton)

        QTimer.singleShot(500, close_d_dialog)
        qtbot.mouseClick(w.btnAddDetector, Qt.LeftButton)
        assert not w.d_dialog


    def test_db_gui_agreement(self, qtbot):
        """
        Assures all scenarios/tests are appearing
        """

        w = Rase([])
        qtbot.addWidget(w)
        session = Session()
        assert w.tblScenario.rowCount() == len(session.query(Scenario).all())
        assert w.tblDetectorReplay.rowCount() == len(session.query(Detector).all())


# Instrument creation and deletion testing
class Test_Inst_Create_Delete:
    def test_detector_create_delete(self):
        """
        Verifies that we can create and delete detectors
        """
        hoc = HelpObjectCreation()
        detector_name = hoc.get_default_detector_name()
        hoc.create_empty_detector()
        session = Session()

        assert session.query(Detector).filter_by(name=detector_name).first()
        delete_instrument(session, detector_name)
        assert not session.query(Detector).filter_by(name=detector_name).first()

    def test_create_delete_with_bspec_and_params(self):
        """
        Verifies that we can create and delete detectors with base spectra and various parameters set
        """
        hoc = HelpObjectCreation()
        detector_name = hoc.get_default_detector_name()
        hoc.create_empty_detector()
        session = Session()

        assert len(session.query(BaseSpectrum).all()) == 0
        baseSpectra = hoc.add_default_base_spectra()
        assert len(baseSpectra)

        detector = session.query(Detector).filter_by(name=detector_name).first()
        for bs in baseSpectra:
            detector.base_spectra.append(bs)
        assert len(session.query(BaseSpectrum).all()) == len(baseSpectra)

        hoc.set_default_detector_params()

        assert session.query(Detector).filter_by(name=detector_name).first()
        delete_instrument(session, detector_name)
        assert not session.query(Detector).filter_by(name=detector_name).first()
        assert len(session.query(SampleSpectraSeed).all()) == 0

    def test_replay_create_delete(self):
        hoc = HelpObjectCreation()
        hoc.create_default_replay()

        session = Session()
        assert session.query(Replay).filter_by(name=hoc.get_default_replay_name()).first()
        replay_delete = session.query(Replay).filter_by(name=hoc.get_default_replay_name())
        replay_delete.delete()
        assert session.query(Replay).filter_by(name=hoc.get_default_replay_name()).first() is None

    def test_detector_create_delete_gui(self, qtbot):
        detector_name = 'test_detector'
        w = Rase([])
        qtbot.addWidget(w)
        w.show()
        qtbot.waitForWindowShown(w)

        def add_detector():
            qtbot.keyClicks(w.d_dialog.txtDetector, detector_name+'\t') #tab at end so the keystrokes get registered and saved when the cursor moves to a new text box.
            qtbot.mouseClick(w.d_dialog.buttonBox.button(QDialogButtonBox.Ok), Qt.LeftButton)

        QTimer.singleShot(100, add_detector)
        qtbot.mouseClick(w.btnAddDetector, Qt.LeftButton)

        helper = Helper()

        def handle_yes():
            messagebox = w.findChild(QMessageBox)
            yes_button = messagebox.button(QMessageBox.Yes)
            QTimer.singleShot(200, helper.finished.emit)
            qtbot.mouseClick(yes_button, Qt.LeftButton, delay=1)

        def handle_timeout():
            menu = None
            for tl in QApplication.topLevelWidgets():
                if isinstance(tl, QMenu) and len(tl.actions()) > 0 and tl.actions()[0].text() == "Delete Instrument":
                    menu = tl
                    break

            assert menu is not None
            delete_action = None

            for action in menu.actions():
                if action.text() == 'Delete Instrument':
                    delete_action = action
                    break
            assert delete_action is not None
            rect = menu.actionGeometry(delete_action)
            QTimer.singleShot(1000, handle_yes)
            qtbot.mouseClick(menu, Qt.LeftButton, pos=rect.center())




        with qtbot.waitSignal(helper.finished, timeout=5 * 1000):
            QTimer.singleShot(1000, handle_timeout)
            item = None
            for row in range(w.tblDetectorReplay.rowCount()):
                if w.tblDetectorReplay.item(row, 0).text() == detector_name:
                    item = w.tblDetectorReplay.item(row, 0)
                    break
            assert item is not None
            rect = w.tblDetectorReplay.visualItemRect(item)
            event = QContextMenuEvent(QContextMenuEvent.Mouse, rect.center())
            QApplication.postEvent(w.tblDetectorReplay.viewport(), event)

        # make sure the detector is not in the database or the instrument table
        assert w.tblDetectorReplay.rowCount() == 0
        session = Session()
        assert not session.query(Detector).filter_by(name=detector_name).first()


# Scenario group creation testing
class Test_ScenGroup_Create_Delete:
    def test_create_scengroup(self):
        group_name = 'group_name'
        session = Session()
        if session.query(ScenarioGroup).filter_by(name=group_name).first():
            gsd.delete_groups(session, group_name)
        gsd.add_groups(session, group_name)
        assert session.query(ScenarioGroup).filter_by(name=group_name).first()

    def test_delete_default_scengroup(self):
        group_name = 'group_name'
        session = Session()
        gsd.delete_groups(session, group_name)
        assert session.query(ScenarioGroup).filter_by(name=group_name).first() is None


# Material and base spectra creation testing
class Test_Material_BaseSpec_Create_Delete:
    def test_create_material(self):
        session = Session()
        matname = 'dummy_mat'
        assert get_or_create_material(session, matname)

    def test_build_background_spectrum(self):
        for mat_name, bin_counts in zip(['dummy_mat_1', 'dummy_mat_2'], [4093, 4621]):
            session = Session()
            baseSpectraFilepath = 'dummy_path.n42'
            realtime = 2887.0
            livetime = 2879.0
            counts_arr = np.array([bin_counts] * 1024)
            counts = [str(a) for a in counts_arr[:-1]] + [str(counts_arr[-1])]
            counts = ', '.join(counts)
            assert BackgroundSpectrum(material=get_or_create_material(session, mat_name),
                                      filename=baseSpectraFilepath,
                                      realtime=realtime, livetime=livetime, baseCounts=counts)

    def test_build_base_spectrum(self):
        session = Session()
        for mat_name, bin_counts in zip(['dummy_mat_1', 'dummy_mat_2'], [4093, 4621]):
            baseSpectraFilepath = 'dummy_path.n42'
            realtime = 2887.0
            livetime = 2879.0
            rase_sensitivity = 12799.1
            flux_sensitivity = 59.2
            counts_arr = np.array([bin_counts] * 1024)
            counts = [str(a) for a in counts_arr[:-1]] + [str(counts_arr[-1])]
            counts = ', '.join(counts)
            assert BaseSpectrum(material=get_or_create_material(session, mat_name),
                                filename=baseSpectraFilepath,
                                realtime=realtime, livetime=livetime,
                                rase_sensitivity=rase_sensitivity, flux_sensitivity=flux_sensitivity,
                                baseCounts=counts)


# Scenario creation testing
class Test_Scen_Create_Delete:
    def test_create_scen(self):

        hoc = HelpObjectCreation()
        session = Session()

        acq_times, replications, fd_mode, fd_mode_back, mat_names, back_names, doses, doses_back = hoc.get_default_scen_pars()
        scenMaterials, bcgkScenMaterials = hoc.create_base_materials(fd_mode, fd_mode_back, mat_names, back_names, doses, doses_back)

        for acqTime, replication, baseSpectrum, backSpectrum in zip(acq_times, replications, scenMaterials, bcgkScenMaterials):
            scen_hash = Scenario.scenario_hash(float(acqTime), baseSpectrum, backSpectrum, [])
            scen_exists = session.query(Scenario).filter_by(id=scen_hash).first()
            if scen_exists:
                root_folder = '.'
                delete_scenario([scen_hash], root_folder)
                assert session.query(Scenario).filter_by(id=scen_hash).first() is None
            session.add(Scenario(float(acqTime), replication, baseSpectrum, backSpectrum, [], hoc.get_scengroups(session)))
        assert len(session.query(Scenario).all()) == 2

    def test_scen_delete(self):
        root_folder = '.'
        session = Session()
        scens = session.query(Scenario).all()
        assert len(scens) == 2
        scen_ids = [scen.id for scen in scens]
        delete_scenario(scen_ids, root_folder)
        assert session.query(Scenario).first() is None


# Results Calculation testing
class Test_Workflow:
    # qtbot is necessary as an argument or errors will occur with trying to create a RASE widget
    def test_spec_gen(self, qtbot):
        hoc = HelpObjectCreation()

        hoc.create_default_workflow()
        sim_context_list = hoc.get_default_workflow()

        assert sim_context_list
        spec_generation = SampleSpectraGeneration(sim_context_list)
        spec_generation.work()

    # Can we run the replay tools and get results?
    def test_run_replay(self, qtbot):
        """Dependent on test_spec_gen running"""
        hoc = HelpObjectCreation()
        session = Session()

        sim_context_list = hoc.get_default_workflow()

        assert sim_context_list

        replay_gen = ReplayGeneration(sim_context_list)
        replay_gen.runReplay()

class Test_Workflow_GUI:

    def select_scen_det(self, w : Rase, qtbot):
        for i in range(w.tblScenario.rowCount()):
            item = w.tblScenario.item(i, 1)
            assert item is not None
            rect = w.tblScenario.visualItemRect(item)
            qtbot.mouseClick(w.tblScenario.viewport(), Qt.LeftButton, stateKey=Qt.KeyboardModifier.ControlModifier, pos=rect.center())
        item = w.tblDetectorReplay.item(0, 1)
        assert item is not None
        rect = w.tblDetectorReplay.visualItemRect(item)
        qtbot.mouseClick(w.tblDetectorReplay.viewport(), Qt.LeftButton, pos=rect.center())
        sim_context_list = w.runSelect()

    def handle_ok(self,w,qtbot):
        messagebox = w.findChild(QMessageBox)
        ok_button = messagebox.button(QMessageBox.Ok)
        # QTimer.singleShot(200, helper.finished.emit)
        qtbot.mouseClick(ok_button, Qt.LeftButton, delay=1)

    def test_select_scen_det(self,qtbot):
        hoc = HelpObjectCreation()
        hoc.create_default_workflow()
        sim_context_list_orig = hoc.get_default_workflow()
        w = Rase([])
        w.show()
        self.select_scen_det(w, qtbot)
        sim_context_list = w.runSelect()
        assert set(sim_context_list_orig) == set(sim_context_list)

    # qtbot is necessary as an argument or errors will occur with trying to create a RASE widget
    def test_spec_gen(self, qtbot):
        hoc = HelpObjectCreation()
        hoc.create_default_workflow()
        # det_names, scen_ids = hoc.get_default_workflow()
        w = Rase([])
        w.show()
        self.select_scen_det(w, qtbot)

        QTimer.singleShot(2000, lambda : self.handle_ok(w,qtbot))
        spec_status = w.on_btnGenerate_clicked(False)
        assert spec_status

    def test_replay_adjust_confidences(self,qtbot):
        hoc = HelpObjectCreation()
        replay=hoc.create_default_replay()
        w = ReplayDialog(parent=None, replay=replay)
        assert not w.cbConfUse.isChecked()
        w.show()
        w.cbConfUse.setChecked(True)
        w.radioConfCont.setChecked(True)

        def handle_conf_table():
            conftable = w.findChild(QDialog, name='dialogConfidence')
            confmodel = conftable.findChild(QObject,'tblConfidence').model()
            confmodel.setDataFromTable([[0,20],[0,1]])
            conftable.accept()

        RaseSettings().setUseConfidencesInCalcs(True)

        QTimer.singleShot(1000, handle_conf_table)
        w.btnConfCont.click()
        assert w.replay.confidence_scale_range
        w.accept()

    # Can we run the replay tools and get results?
    def test_run_replay(self, qtbot):
        """Dependent on test_spec_gen running"""
        hoc = HelpObjectCreation()
        # hoc.create_default_workflow()
        # det_names, scen_ids = hoc.get_default_workflow()
        w = Rase([])
        w.show()
        self.select_scen_det(w, qtbot)
        QTimer.singleShot(2000, lambda: self.handle_ok(w, qtbot))
        replay_status = w.on_btnRunReplay_clicked(False)
        assert replay_status

    def test_results_calc(self, qtbot):
        """Dependent on test_spec_gen and test_run_replay running"""
        hoc = HelpObjectCreation()
        w = Rase([])

        sim_context_list = hoc.get_default_workflow()
        assert sim_context_list

        def close_dialog():
            focused_widget = QApplication.activeModalWidget()
            assert focused_widget
            qtbot.keyClick(focused_widget, Qt.Key.Key_Return)
        QTimer.singleShot(500, close_dialog)
        QTimer.singleShot(1000, close_dialog)
        result_super_map, scenario_stats_df = calculateScenarioStats(sim_context_list, gui=w)
        assert len(scenario_stats_df) == 2
        assert scenario_stats_df['PID'][0] == 1.0
        assert scenario_stats_df['PID'][1] == 0.0
        assert scenario_stats_df['wTP'][0] == 0.25 #0.25 because fixed_replay gives confidence = 5 and the confidence table update makes reported 20 = weight 1.

# Sampling testing
class Test_Sampling:
    def test_sampling_algos(self):
        from src.sampling_algos import generate_sample_counts_rejection as s_rejection
        from src.sampling_algos import generate_sample_counts_inversion as s_inversion
        from src.sampling_algos import generate_sample_counts_poisson as s_poisson

        class Scenario:
            pass
        class Detector:
            pass

        s = Scenario()
        d = Detector()

        s.acq_time = 120
        d.chan_count = 1024
        seed = 1
        counts = np.array([4093] * d.chan_count)
        dose = .13
        sensitivity = 17377
        c_d_s = [(counts, dose, sensitivity)]

        sample_counts_r = s_rejection(s, d, c_d_s, seed)
        sample_counts_i = s_inversion(s, d, c_d_s, seed)
        sample_counts_p = s_poisson(s, d, c_d_s, seed)
        rip = [sample_counts_r, sample_counts_i, sample_counts_p]
        sum_rip = [sum(r) for r in rip]
        min_sqrt_rip = min([np.sqrt(sc) for sc in sum_rip])

        for sc in rip:
            assert len(sc) == d.chan_count
        assert max(sum_rip) - min(sum_rip) < min_sqrt_rip

# class Test_Shielding:
#
#     def test_shielding_creation(self):
#         """
#         Verifies that we can create and delete detectors
#         """
#         # can this be ported to fixtures?
#         session = Session()
#         bscmodel = BaseSpectraLoadModel()
#         bscmodel.get_spectra_data(generic_nai_spectra)
#         bscmodel.accept()
#         dmodel = DetectorModel('test_from_basespectra')
#         dmodel.assign_spectra(bscmodel)
#
#
#
#     def test_it_matmul(self):
#         shield_default = {'det_name': 'Dummy',
#                           'ch_num': 1024,
#                           'ecals': [0, 3, 0, 0]}
#         shield_mod = ShieldingModule([k for k in shield_default.values()])
#         matrix_a = np.array([[1,1,1],[2,2,2],[3,3,3]])
#         matrix_b = np.array([[4,4,4],[5,5,5],[6,6,6]])
#         matrix_c = np.array([[7,7,7],[8,8,8],[9,9,9]])
#         assert (np.array([[360,360],[720,720]]) == shield_mod.iterative_matmul((matrix_a[:2, :],
#                                                                 np.matmul(matrix_c, matrix_b[:, :2])))).all()
#

class Test_Import_Export:
    hoc = HelpObjectCreation()
    def test_export(self, qtbot):
        settings = RaseSettings()
        file_target = Path(settings.getDataDirectory()) / 'test_export.yaml'
        hoc = HelpObjectCreation()
        hoc.create_default_workflow()
        sim_context_list = hoc.get_default_workflow()
        d_dialog = DetectorDialog(None, sim_context_list[0].detector.name)
        d_dialog.on_btnExportDetector_clicked(savefilepath=file_target)

    def test_import(self, qtbot):
        settings = RaseSettings()
        file_target = Path(settings.getDataDirectory()) / 'test_export.yaml'
        hoc = HelpObjectCreation()
        hoc.get_default_workflow()
        d_dialog = DetectorDialog(None)
        d_dialog.on_btnImportDetector_clicked(importfilepath=file_target)
        d_dialog.accept()

        d_dialog = DetectorDialog(None)
        d_dialog.on_btnImportDetector_clicked(importfilepath=file_target)
        d_dialog.accept()

    def test_delete_new(self):
        session= Session()
        sim_context_list = self.hoc.get_default_workflow()
        det_name = sim_context_list[0].detector.name
        delete_instrument(Session(), det_name +'_Imported')
        delete_instrument(Session(), det_name + '_Imported_Imported')
        assert not session.query(Detector).filter_by(name=det_name +'_Imported').first()
        assert not session.query(Detector).filter_by(name=det_name + '_Imported_Imported').first()

    def test_open_old(self):
        sim_context_list = self.hoc.get_default_workflow()
        d_dialog = DetectorDialog(None, sim_context_list[0].detector.name)
        d_dialog.show()
        d_dialog.accept()

    def test_import_model(self):
        session = Session()
        dmodel = DetectorModel()
        sim_context_list = self.hoc.get_default_workflow()
        det_name = sim_context_list[0].detector.name
        assert not dmodel.reinitialize_detector(det_name +'_extra_nonsense_not_real_detector')
        settings = RaseSettings()
        file_target = Path(settings.getDataDirectory()) / 'test_export.yaml'
        dmodel.import_from_file(file_target)
        session.query(Detector).filter_by(name=dmodel.detector.name).one() #raise if none
        dmodel2 = DetectorModel(det_name)
        assert dmodel2.detector.name == det_name


from src.base_spectra_dialog import BaseSpectraLoadModel
class Test_Model_View:

    def test_create_detector(self, dummy_base_spectrum):
        session = Session()
        bscmodel = BaseSpectraLoadModel()
        bscmodel.get_spectra_data(dummy_base_spectrum)
        bscmodel.accept()
        dmodel = DetectorModel('test_from_basespectra')
        dmodel.assign_spectra(bscmodel)
        replay = ReplayModel(name='Test')
        replay.exe_path = f"{Path(__file__).parent / '../tools/fixed_replay.py'}"
        replay.accept()
        dmodel.set_replay('Test')
        dmodel.accept()


        # # TODO: API-ify the replay tool and make sure it exists
        # hoc = HelpObjectCreation()
        # hoc.create_default_replay()
        #
        # dmodel.set_replay(hoc.get_default_replay_name())
        # dmodel.accept()
        # test if detector now exists in session
        assert session.query(Detector).filter_by(name='test_from_basespectra').first() is not None
