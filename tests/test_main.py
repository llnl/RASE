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

from time import sleep

import pytest
from PySide6.QtCore import Qt, QTimer, QObject
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QDialogButtonBox, QMenu, QApplication, QMessageBox, QDialog
from sqlalchemy.testing.plugin.plugin_base import fixtures

from src.detector_dialog import DetectorDialog, DetectorModel
from src.replay_dialog import ReplayModel
from src.rase import Rase
from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.results_calculation import calculateScenarioStats
from src.scenario_group_dialog import GroupSettings as gsd
from src.table_def import ScenarioGroup, Replay, ShieldedSpectrum, Detector, Scenario, BaseSpectrum
from src.template_conversion_tool_dialog import TemplateConversionDialog, TemplateConversionModel
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.orm.session import _sessions
from src.spectra_generation import SampleSpectraGeneration
from src.contexts import SimContext
from src.rase_init import init_rase
from src.replay_generation import ReplayGeneration
from src.replay_dialog import ReplayDialog
from src.create_shielded_spectra_dialog import ShieldingModule, CreateShieldedSpectraDialog

# pytest.main(['-s'])
from .fixtures import (db_and_output_folder, dummy_base_spectrum, generic_nai_spectra, temp_data_dir,
                       HelpObjectCreation, Helper, cleanup)



# Database testing
class Test_Database:

   # removed test to set data directory, since this is set in a fixture used by other tests and shouldn't be altered here.
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
            d = QApplication.activeWindow()
            assert d.windowTitle() == "Add Instrument"
            qtbot.mouseClick(d.buttonBox.button(QDialogButtonBox.Cancel), Qt.LeftButton)

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
            d = QApplication.activeWindow()
            assert d.windowTitle() == "Add Instrument"
            qtbot.mouseClick(d.buttonBox.button(QDialogButtonBox.Cancel), Qt.LeftButton)

        def is_rase_active():
            # need to wait a tick for the main window to resume being active
            win = QApplication.activeWindow()
            return win is not None

        QTimer.singleShot(500, close_d_dialog)
        qtbot.mouseClick(w.btnAddDetector, Qt.LeftButton)

        qtbot.waitUntil(is_rase_active, timeout=1)
        assert QApplication.activeWindow().windowTitle() == "RASE"


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
            d = QApplication.activeWindow()
            assert d.windowTitle() == "Add Instrument"
            qtbot.keyClicks(d.txtDetector, detector_name+'\t') #tab at end so the keystrokes get registered and saved when the cursor moves to a new text box.
            qtbot.mouseClick(d.buttonBox.button(QDialogButtonBox.Ok), Qt.LeftButton)

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

    def test_detector_add_bases(self,qtbot, generic_nai_spectra):
        detector_name = 'test_detector'
        from src.base_spectra_dialog import BaseSpectraDialog
        d = DetectorDialog(None, detector_name)
        helper = Helper()

        basespec_dialog = BaseSpectraDialog()

        def add_bases_actions():
            basespec_dialog.on_btnBrowse_clicked(False, directoryPath= generic_nai_spectra)
            basespec_dialog.accept()
            helper.finished.emit()

        QTimer.singleShot(500, add_bases_actions)

        d.on_btnAddBaseSpectra_clicked(True, dlg=basespec_dialog)

        # Wait for the helper signal to ensure the dialog interaction is complete
        with qtbot.waitSignal(helper.finished, timeout=5 * 1000):
            d.btnRemoveBaseSpectra.click()
            QTimer.singleShot(500, add_bases_actions)
            d.on_btnAddBaseSpectra_clicked(True, dlg=basespec_dialog)

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
                delete_scenarios([scen_hash], root_folder)
                assert session.query(Scenario).filter_by(id=scen_hash).first() is None
            session.add(Scenario(float(acqTime), replication, baseSpectrum, backSpectrum, [], hoc.get_scengroups(session)))
        assert len(session.query(Scenario).all()) == 2

    def test_scen_delete(self):
        root_folder = '.'
        session = Session()
        scens = session.query(Scenario).all()
        assert len(scens) == 2
        scen_ids = [scen.id for scen in scens]
        delete_scenarios(scen_ids, root_folder)
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

        QTimer.singleShot(3000, lambda : self.handle_ok(w,qtbot))
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
        QTimer.singleShot(3000, lambda: self.handle_ok(w, qtbot))
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


class Test_Shielding:
    @pytest.fixture(scope="class")
    def setup_environment(self, temp_data_dir):
        """Fixture to initialize the RASE environment and return shared paths and parameters."""
        datadir = temp_data_dir
        init_rase(datadir)
        return datadir

    @pytest.fixture(scope="class")
    def setup_detectorargs(self, temp_data_dir):
        return (Path(__file__).parent.parent / 'baseSpectra' / 'genericNaI', 'dummy', 'scenario')

    @pytest.fixture(scope="class")
    def setup_paths(self, temp_data_dir):
        # Shared paths
        null_root_path = Path(__file__).parent.parent / 'shielding_library' / 'FinalShieldingConfigs' / '1024'
        shield_root_path = Path(__file__).parent.parent / 'shielding_library' / 'FinalInstrumentConfigs' / '1024'
        paths = {
            'path_drfinv': shield_root_path / 'GenericNaI_2x2_betterresolution_0_3_0_bins1024_responsed1024_0.01_inverted.npz',
            'path_drf': shield_root_path / 'GenericNaI_2x2_betterresolution_0_3_0_bins1024_responsed1024_specs.npz',
            'path_nullinv': null_root_path / 'Null_0_3_0_bins1024_responsed1024_0.01_inverted.npz',
            'path_nullshield_thin': null_root_path / 'Null_0_3_0_bins1024_responsed1024_0.26cmSS_specs.npz',
            'path_nullshield_thick': null_root_path / 'Null_0_3_0_bins1024_responsed1024_1cmSS_specs.npz',
            'path_nullshield_gadras': null_root_path / 'Null_0_3_0_bins1024_responsed1024_0.5cmSS_specs.npz',
            'interp_thickness': 0.5
        }
        return paths

    @pytest.fixture(scope="class")
    def create_detector(self, setup_environment, setup_detectorargs):
        """Fixture to create the detector."""
        _ = setup_environment
        base_spec_dir, detector_name, secondary_type = setup_detectorargs

        bscmodel = BaseSpectraLoadModel()
        bscmodel.get_spectra_data(base_spec_dir)
        bscmodel.accept()

        dmodel = DetectorModel(detector_name)
        dmodel.delete_relations()
        dmodel.assign_spectra(bscmodel)
        dmodel.detector_type_secondary = secondary_type
        dmodel.accept()

        return dmodel.detector

    @pytest.fixture(scope="class")
    def prepare_shielding_data(self, create_detector, setup_paths):
        detector = create_detector
        paths = setup_paths

        model = ShieldingModule('Test')
        og_spec = detector.base_spectra[-1]
        ecals = (og_spec.ecal0, og_spec.ecal1, og_spec.ecal2, og_spec.ecal3)
        energies = np.polyval(list(reversed(ecals)), np.linspace(0, 1024, 1024))

        rebinned_counts = model.rebin_spec_todrf(og_spec)
        matrix_nullinv = model.load_matrix(paths['path_nullinv'])
        matrix_drf = model.load_matrix(paths['path_drf'])
        matrix_drfinv = model.load_matrix(paths['path_drfinv'])

        T_thn = model.get_T(matrix_nullinv, model.load_matrix(paths['path_nullshield_thin']))
        T_thk = model.get_T(matrix_nullinv, model.load_matrix(paths['path_nullshield_thick']))

        shielded_counts_thn = model.iterative_matmul([matrix_drf, T_thn, matrix_drfinv, rebinned_counts])
        outcounts_thn = model.rebin_spec_tomeasured(shielded_counts_thn, ecals)

        shielded_counts_thk = model.iterative_matmul([matrix_drf, T_thk, matrix_drfinv, rebinned_counts])
        outcounts_thk = model.rebin_spec_tomeasured(shielded_counts_thk, ecals)

        return {
            'model': model,
            'og_spec': og_spec,
            'ecals': ecals,
            'energies': energies,
            'rebinned_counts': rebinned_counts,
            'matrix_nullinv': matrix_nullinv,
            'matrix_drf': matrix_drf,
            'matrix_drfinv': matrix_drfinv,
            'outcounts_thn': outcounts_thn,
            'outcounts_thk': outcounts_thk
        }

    def test_it_matmul(self):
        """Verify iterative_matmul multiplies a sequence correctly."""
        shield_default = {'det_name': 'Dummy',
                          'ch_num': 1024,
                          'ecals': [0, 3, 0, 0]}
        shield_mod = ShieldingModule([k for k in shield_default.values()])
        matrix_a = np.array([[1,1,1],[2,2,2],[3,3,3]])
        matrix_b = np.array([[4,4,4],[5,5,5],[6,6,6]])
        matrix_c = np.array([[7,7,7],[8,8,8],[9,9,9]])
        assert (np.array([[360,360],[720,720]]) == shield_mod.iterative_matmul(
                            (matrix_a[:2, :], np.matmul(matrix_c, matrix_b[:, :2])))).all()

    def test_load_responses(self, setup_paths):
        """Load shielding/DRF matrices and spot-check expected values."""
        paths = setup_paths
        model = ShieldingModule('Test')
        null_responses, drf_responses = model.load_responses(paths['path_nullinv'], paths['path_nullshield_thick'],
                                                             paths['path_drfinv'], paths['path_drf'])
        # pick various points around the matrices
        assert null_responses[0][0,0] == 0
        assert null_responses[0][1, 1] == pytest.approx(7.58e-8)
        assert null_responses[0][100, 100] == pytest.approx(7.58e-8)
        assert null_responses[0][500, 500] == pytest.approx(7.58e-8)
        assert null_responses[0][101, 100] == pytest.approx(0)
        assert null_responses[0][400, 930] == pytest.approx(0)

        assert null_responses[1][0,0] == pytest.approx(0)
        assert null_responses[1][18,78] == pytest.approx(34.3)
        assert null_responses[1][145, 653] == pytest.approx(7860)
        assert null_responses[1][653, 145] == pytest.approx(0)
        assert null_responses[1][832, 832] == pytest.approx( 9720000)

        assert drf_responses[0][0,0] == pytest.approx(0)
        assert drf_responses[0][17,32] == pytest.approx(-7.4e-8)
        assert drf_responses[0][195,589] == pytest.approx(-1.14e-8)
        assert drf_responses[0][923,243] == pytest.approx(5.39e-9)

        assert drf_responses[1][0,0] == pytest.approx(0)
        assert drf_responses[1][148,302] == pytest.approx(11500)
        assert drf_responses[1][443,231] == pytest.approx(0)
        assert drf_responses[1][934,967] == pytest.approx(330)

    def test_shielding_basic(self, prepare_shielding_data):
        """Basic sanity: lengths and attenuation ordering for discrete shields."""
        data = prepare_shielding_data

        assert len(data['outcounts_thn']) == len(data['energies']), '1cm shielded counts length mismatch.'
        assert len(data['outcounts_thk']) == len(data['energies']), '0.26cm shielded counts length mismatch.'
        assert max(data['outcounts_thk']) < max(data['outcounts_thn']) < max(data['og_spec'].counts)

    def test_shielding_interpolation(self, setup_environment, setup_paths, prepare_shielding_data):
        """Interpolation vs discrete (0.5 cm): shape and boundedness checks."""
        paths = setup_paths
        data = prepare_shielding_data

        interp_matrices = {
            0.26: paths['path_nullshield_thin'],
            1: paths['path_nullshield_thick']
        }

        T_interp = data['model'].interpolate_response(thickness=paths['interp_thickness'], matrices=interp_matrices,
                                                      inv=paths['path_nullinv'])
        T_gad = data['model'].get_T(data['matrix_nullinv'], data['model'].load_matrix(paths['path_nullshield_gadras']))

        shielded_counts_interp = data['model'].iterative_matmul([data['matrix_drf'], T_interp, data['matrix_drfinv'],
                                                                 data['rebinned_counts']])
        outcounts_interp = data['model'].rebin_spec_tomeasured(shielded_counts_interp, data['ecals'])
        shielded_counts_gad = data['model'].iterative_matmul([data['matrix_drf'], T_gad, data['matrix_drfinv'],
                                                              data['rebinned_counts']])
        outcounts_gad = data['model'].rebin_spec_tomeasured(shielded_counts_gad, data['ecals'])

        assert len(outcounts_interp) == len(data['energies']), 'Interpolated shielded counts length mismatch.'
        assert len(outcounts_gad) == len(data['energies']), 'GADRAS shielded counts length mismatch.'
        assert (max(data['outcounts_thk']) < max(outcounts_interp) <
                max(data['outcounts_thn']) < max(data['og_spec'].counts))

        tolerance = 0.05
        assert max(np.where((outcounts_gad > 40) & (outcounts_interp > 40),
                            outcounts_gad / outcounts_interp, 1)) - 1 < tolerance

    def test_interpolate_below_min_thickness(self, setup_paths, prepare_shielding_data):
        """Extrapolation below minimum thickness returns between none and thinnest."""
        paths = setup_paths
        data = prepare_shielding_data

        interp_matrices = {
            0.26: paths['path_nullshield_thin'],
            1: paths['path_nullshield_thick']
        }
        # thickness below min(0.26)
        t_small = 0.1
        T_small = data['model'].interpolate_response(thickness=t_small, matrices=interp_matrices,
                                                      inv=paths['path_nullinv'])

        # Identity (no shielding)
        I = np.eye(data['matrix_nullinv'].shape[0])
        drf, drfinv = data['matrix_drf'], data['matrix_drfinv']
        rb = data['rebinned_counts']

        out_small = data['model'].rebin_spec_tomeasured(
            data['model'].iterative_matmul([drf, T_small, drfinv, rb]), data['ecals'])
        out_thin = data['outcounts_thn']
        out_none = data['model'].get_outcounts(I, [drfinv, drf], data['og_spec'])

        assert len(out_small) == len(data['energies'])
        assert max(out_thin) < max(out_small) < max(out_none)

    def test_interpolate_above_max_thickness(self, setup_paths, prepare_shielding_data):
        """Extrapolation above maximum thickness yields stronger attenuation than thickest."""
        paths = setup_paths
        data = prepare_shielding_data

        interp_matrices = {
            0.26: paths['path_nullshield_thin'],
            1: paths['path_nullshield_thick']
        }
        # thickness above max(1)
        t_large = 2.0
        T_large = data['model'].interpolate_response(thickness=t_large, matrices=interp_matrices,
                                                     inv=paths['path_nullinv'])

        drf, drfinv = data['matrix_drf'], data['matrix_drfinv']
        rb = data['rebinned_counts']
        out_large = data['model'].rebin_spec_tomeasured(
            data['model'].iterative_matmul([drf, T_large, drfinv, rb]), data['ecals'])

        # Identity (no shielding)
        I = np.eye(data['matrix_nullinv'].shape[0])
        out_none = data['model'].get_outcounts(I, [drfinv, drf], data['og_spec'])
        out_thk = data['outcounts_thk']

        assert len(out_large) == len(data['energies'])
        assert max(out_large) < max(out_thk) < max(out_none)

    def test_get_outcounts_identity_roundtrip(self, setup_paths, prepare_shielding_data):
        """Using identity T reproduces original counts (bins 20–200 within tolerance)."""
        data = prepare_shielding_data
        I = np.eye(data['matrix_nullinv'].shape[0])
        out_identity = data['model'].get_outcounts(I, [data['matrix_drfinv'], data['matrix_drf']], data['og_spec'])
        # Round-trip should approximately recover original counts
        assert len(out_identity) == len(data['og_spec'].counts)
        assert np.isfinite(out_identity).all()
        assert np.max(out_identity) > 0
        expected_counts = data['og_spec'].counts
        s, e = 85, 140  # flat region post oscillation reduction
        assert np.allclose(out_identity[s:e], expected_counts[s:e], rtol=1e-3, atol=1e-6)

    def test_process_matrices_matches_manual(self, setup_paths, prepare_shielding_data):
        """process_matrices equals get_T + get_outcounts for the same inputs."""
        paths = setup_paths
        data = prepare_shielding_data
        null_responses = [data['matrix_nullinv'], data['model'].load_matrix(paths['path_nullshield_thin'])]
        drf_responses = [data['matrix_drfinv'], data['matrix_drf']]
        out_proc = data['model'].process_matrices(null_responses, drf_responses, data['og_spec'])

        T = data['model'].get_T(*null_responses)
        out_manual = data['model'].get_outcounts(T, drf_responses, data['og_spec'])

        assert np.allclose(out_proc, out_manual, rtol=1e-5, atol=1e-5)

    def test_load_responses_shape_mismatch_raises(self, temp_data_dir):
        """load_responses raises on incompatible shapes (AssertionError/ValueError)."""
        model = ShieldingModule('Test')
        tmp = Path(RaseSettings().getSampleDirectory()) / 'shield_shape_tests'
        tmp.mkdir(parents=True, exist_ok=True)

        # Helper to write npz with key 'data'
        def w(p, arr):
            np.savez(p, data=arr)

        # 1) Null shapes incompatible
        nullinv_1 = tmp / 'ninv1.npz'
        nullshield_1 = tmp / 'nsh1.npz'
        drfinv_1 = tmp / 'dinv1.npz'
        drf_1 = tmp / 'drf1.npz'
        w(nullinv_1, np.zeros((2, 3)))
        w(nullshield_1, np.zeros((2, 3)))  # should be (3,2)
        w(drfinv_1, np.zeros((2, 3)))
        w(drf_1, np.zeros((3, 2)))
        with pytest.raises((AssertionError, ValueError)):
            model.load_responses(nullinv_1, nullshield_1, drfinv_1, drf_1)

        # 2) DRF shapes incompatible
        nullinv_2 = tmp / 'ninv2.npz'
        nullshield_2 = tmp / 'nsh2.npz'
        drfinv_2 = tmp / 'dinv2.npz'
        drf_2 = tmp / 'drf2.npz'
        w(nullinv_2, np.zeros((2, 3)))
        w(nullshield_2, np.zeros((3, 2)))  # ok for null pair
        w(drfinv_2, np.zeros((2, 3)))
        w(drf_2, np.zeros((2, 3)))  # should be (3,2)
        with pytest.raises((AssertionError, ValueError)):
            model.load_responses(nullinv_2, nullshield_2, drfinv_2, drf_2)

        # 3) DRF/Null incompatible 0-dim mismatch
        nullinv_3 = tmp / 'ninv3.npz'
        nullshield_3 = tmp / 'nsh3.npz'
        drfinv_3 = tmp / 'dinv3.npz'
        drf_3 = tmp / 'drf3.npz'
        w(nullinv_3, np.zeros((2, 3)))
        w(nullshield_3, np.zeros((3, 2)))
        w(drfinv_3, np.zeros((4, 5)))
        w(drf_3, np.zeros((5, 4)))
        with pytest.raises((AssertionError, ValueError)):
            model.load_responses(nullinv_3, nullshield_3, drfinv_3, drf_3)

    def test_gen_shielded_specs_creates_records(self):
        """Exact shielding: spectra_generation creates ShieldedSpectrum DB records (discrete thickness)."""
        # Build default workflow and then set shielding on a scenario
        hoc = HelpObjectCreation()
        hoc.create_default_workflow()
        session = Session()
        detector = session.query(Detector).filter_by(name=hoc.get_default_detector_name()).first()
        assert detector is not None
        # choose a scenario with Cs137 present
        scen = session.query(Scenario).first()
        scen.shielding_material = 'Stainless Steel'
        scen.shielding_thickness = 1.0  # exact pick point exists
        session.commit()

        sim_context = [SimContext(detector=detector, replay=None, scenario=scen)]
        gen = SampleSpectraGeneration(sim_context)
        # creation occurs in __init__ via _gen_shielded_specs
        shielded = session.query(ShieldedSpectrum).filter_by(detector_name=detector.name,
                                                             shielding_material=scen.shielding_material,
                                                             shielding_thickness=scen.shielding_thickness).all()
        assert len(shielded) >= 1

    def test_gen_shielded_specs_creates_records_interpolated(self):
        """Interpolated shielding: SampleSpectraGeneration creates ShieldedSpectrum for non-discrete thickness."""
        hoc = HelpObjectCreation()
        hoc.create_default_workflow()
        session = Session()
        detector = session.query(Detector).filter_by(name=hoc.get_default_detector_name()).first()
        scen = session.query(Scenario).first()
        scen.shielding_material = 'Stainless Steel'
        scen.shielding_thickness = 0.8  # not discrete; forces interpolation
        session.commit()

        sim_context = [SimContext(detector=detector, replay=None, scenario=scen)]
        _ = SampleSpectraGeneration(sim_context)

        shielded = session.query(ShieldedSpectrum).filter_by(
            detector_name=detector.name,
            shielding_material=scen.shielding_material,
            shielding_thickness=scen.shielding_thickness,
        ).all()
        assert len(shielded) >= 1

    def test_expected_values_discrete(self, setup_paths, prepare_shielding_data, generic_nai_spectra):
        """Compare 1cm SS output counts to goldens at tests/comparison_shielding."""
        data = prepare_shielding_data
        expected_file = Path(__file__).parent / 'comparison_shielding' / 'outcounts_GenericNaI_SS_1cm_cs137.npz'
        assert expected_file.exists(), f"Missing golden file: {expected_file}"
        expected = np.load(expected_file, allow_pickle=False)['data']
        # Compute discrete 1cm output for Cs137 from file (DB-independent)
        cs_path = Path(generic_nai_spectra) / 'VGeneric_MNaI2x2_Cs137.n42'
        root = etree.parse(str(cs_path)).getroot()
        counts = np.array([float(x) for x in root.find('.//ChannelData').text.strip().split()])
        ecal = [float(x) for x in root.find('.//EnergyCalibration/CoefficientValues').text.strip().split()]
        spec = BaseSpectrum(counts=counts, ecal=ecal, realtime=1.0, livetime=1.0, rase_sensitivity=np.nan, flux_sensitivity=np.nan)
        T_1 = data['model'].get_T(data['matrix_nullinv'], data['model'].load_matrix(setup_paths['path_nullshield_thick']))
        out_cs_1 = data['model'].get_outcounts(T_1, [data['matrix_drfinv'], data['matrix_drf']], spec)
        assert len(expected) == len(out_cs_1)
        # Allow small numeric variation across SciPy/BLAS builds (~0.1% rel)
        s, e = 20, 240  # high stats region
        assert np.allclose(out_cs_1[s:e], expected[s:e], rtol=1e-4, atol=1e-6)

    def test_expected_values_interpolated(self, setup_paths, prepare_shielding_data, generic_nai_spectra):
        """Compare interpolated 0.5 cm SS output counts to golden (bins 20–240 within 5%)."""
        paths = setup_paths
        data = prepare_shielding_data
        expected_file = Path(__file__).parent / 'comparison_shielding' / 'outcounts_GenericNaI_SS_0.5cm_cs137.npz'
        assert expected_file.exists(), f"Missing golden file: {expected_file}"
        expected = np.load(expected_file, allow_pickle=False)['data']
        # Compute interpolated output for Cs137 directly from file (DB-independent)
        cs_path = Path(generic_nai_spectra) / 'VGeneric_MNaI2x2_Cs137.n42'
        root = etree.parse(str(cs_path)).getroot()
        counts = np.array([float(x) for x in root.find('.//ChannelData').text.strip().split()])
        ecal = [float(x) for x in root.find('.//EnergyCalibration/CoefficientValues').text.strip().split()]
        spec = BaseSpectrum(counts=counts, ecal=ecal, realtime=1.0, livetime=1.0, rase_sensitivity=np.nan, flux_sensitivity=np.nan)
        interp_matrices = {0.26: paths['path_nullshield_thin'], 1: paths['path_nullshield_thick']}
        T_interp = data['model'].interpolate_response(thickness=paths['interp_thickness'], matrices=interp_matrices,
                                                      inv=paths['path_nullinv'])
        out_interp = data['model'].get_outcounts(T_interp, [data['matrix_drfinv'], data['matrix_drf']], spec)
        s, e = 20, 240
        assert np.allclose(out_interp[s:e], expected[s:e], rtol=5e-2, atol=1e-6)

    def test_expected_values_interpolated_075(self, setup_paths, prepare_shielding_data, generic_nai_spectra):
        """Compare interpolated 0.75 cm SS output counts to interpolated golden (bins 20–240)."""
        from lxml import etree
        paths = setup_paths
        data = prepare_shielding_data
        expected_file = Path(__file__).parent / 'comparison_shielding' / 'outcounts_GenericNaI_SS_interpolated0.75cm_cs137.npz'
        assert expected_file.exists(), f"Missing golden file: {expected_file}"
        expected = np.load(expected_file, allow_pickle=False)['data']

        # Build spec directly from file
        cs_path = Path(generic_nai_spectra) / 'VGeneric_MNaI2x2_Cs137.n42'
        root = etree.parse(str(cs_path)).getroot()
        counts = np.array([float(x) for x in root.find('.//ChannelData').text.strip().split()])
        ecal = [float(x) for x in root.find('.//EnergyCalibration/CoefficientValues').text.strip().split()]
        from src.table_def import BaseSpectrum as BS
        spec = BS(counts=counts, ecal=ecal, realtime=1.0, livetime=1.0, rase_sensitivity=np.nan, flux_sensitivity=np.nan)

        # Interpolate between 0.5 cm and 1.0 cm
        matrices = {0.5: paths['path_nullshield_gadras'], 1.0: paths['path_nullshield_thick']}
        T_interp = data['model'].interpolate_response(0.75, matrices, inv=paths['path_nullinv'])
        out_interp = data['model'].get_outcounts(T_interp, [data['matrix_drfinv'], data['matrix_drf']], spec)

        s, e = 20, 240
        assert np.allclose(out_interp[s:e], expected[s:e], rtol=5e-2, atol=1e-6)


class Test_Shielding_GUI:
    def test_shielding_dialog_process_without_user_input(self, qtbot, generic_nai_spectra, temp_data_dir):
        """Run shielding dialog model operations programmatically to produce one shielded spectrum."""
        # Create a detector from generic NaI spectra
        session = Session()
        det_name = 'shield_gui_test'
        bscmodel = BaseSpectraLoadModel()
        bscmodel.get_spectra_data(generic_nai_spectra)
        bscmodel.accept()
        dmodel = DetectorModel(det_name)
        dmodel.delete_relations()
        dmodel.assign_spectra(bscmodel)
        dmodel.accept()

        dlg = CreateShieldedSpectraDialog(None, detectorName=det_name)
        qtbot.addWidget(dlg)
        # Use model directly to add one config without GUI clicks
        model = dlg.model
        det = model.data(model.column_dict['detector'])
        drf = model.data(model.column_dict['drf'])
        shieldings = model.shieldings
        shield = 'Stainless Steel' if 'Stainless Steel' in shieldings else shieldings[0]
        # choose one base spectrum and one thickness to keep test quick
        assert model.modelBSL.rowCount() > 0
        base_spectrum_names = [model.modelBSL.data(model.modelBSL.index(0, 0), Qt.DisplayRole)]
        # ensure thicknesses are populated
        model.set_shieldings_from_drf(drf)
        model.setData(model.column_dict['shielding'], shield)
        model.set_thickness()
        thicknesses = list(model.modelThick.model_data.keys())
        assert thicknesses, 'No shield thickness options found'
        selected_thicknesses = [thicknesses[0]]

        model.add_spectra(det, drf, shield, base_spectrum_names, selected_thicknesses)
        shieldmod, spectra = model.process_shielding()
        assert spectra is not None and len(spectra) == 1
        assert isinstance(spectra[0], BaseSpectrum)


class Test_Import_Export:
    hoc = HelpObjectCreation()
    def test_export(self, qtbot, temp_data_dir):
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


class Test_Template_Conversion:
    import pytest

    @pytest.fixture
    def dialog(self, qtbot):
        """Fixture to create and return the TemplateConversionDialog."""
        dlg = TemplateConversionDialog()
        qtbot.addWidget(dlg)
        return dlg

    @pytest.fixture
    def model(self):
        """Fixture to create and return the TemplateConversionModel."""
        return TemplateConversionModel()

    def test_dialog_initialization(self, dialog):
        """Test that the dialog initializes correctly."""
        settings = RaseSettings()
        assert dialog.cmbInputTemplate.count() > 0  # ComboBox should have items
        assert dialog.txtConfigPath.text() == settings.getBaseSpectrumCreationConfig()
        assert dialog.txtTemplatePath.text() == ""  # Template path should be empty initially
        assert dialog.txtInputPath.text() == ""  # Input path should be empty initially
        assert dialog.txtOutputPath.text() == ""  # Output path should be empty initially

    def test_model_initialization(self, model):
        """Test that the model initializes correctly."""
        settings = RaseSettings()
        from src.base_building_algos import default_config
        assert model.rowCount() == 1
        assert model.columnCount() == 5
        assert model.data(model.fields['input_data_format']) == list(default_config.keys())[0]  # Input data format
        assert model.data(model.fields['path_input_config']) == settings.getBaseSpectrumCreationConfig()  # Path input config
        assert model.data(model.fields['path_output_template']) == ""  # Path output template
        assert model.data(model.fields['path_input_folder']) == ""  # Path input folder
        assert model.data(model.fields['path_output_folder']) == ""  # Path output folder

    def test_set_data(self, model):
        """Test setting data in the model."""
        index = model.fields['path_input_config']  # Path input config, index=(0,1)
        configpath = str(Path(__file__).parent.parent / 'configs/base_spectra_config.yaml')
        assert model.setData(index, configpath, Qt.EditRole)
        assert model.data(index) == configpath
        index = model.fields['path_output_template']  # index=(0, 2)
        templatepath = str(Path(__file__).parent.parent / 'n42Templates/rase_n42_template.n42')
        assert model.setData(index, templatepath, Qt.EditRole)
        assert model.data(index) == templatepath
        index = model.fields['path_input_folder']  # index=(0, 3)
        inputpath = str(Path(__file__).parent.parent / 'tests/example_template_conversion/in')
        assert model.setData(index, inputpath, Qt.EditRole)
        assert model.data(index) == inputpath
        index = model.fields['path_output_folder']  # index=(0, 4)
        outpath = str(Path(__file__).parent.parent / 'tests/example_template_conversion/out')
        assert model.setData(index, outpath, Qt.EditRole)
        assert model.data(index) == outpath

        model.reset_data()
        index = model.fields['path_input_config']
        configpath = ''
        assert model.setData(index, configpath, Qt.EditRole)
        assert model.data(index) == configpath

    def test_dialog_combo_box_population(self, dialog):
        """Test that the combo box is populated correctly automatically by setup_combo()."""
        dialog.txtConfigPath.setText('')
        assert dialog.cmbInputTemplate.count() == 3  # ComboBox should have only 'default n42', 'rase n42', and 'PCF file'
        dialog.txtConfigPath.setText(str(Path(__file__).parent.parent / 'configs/base_spectra_config.yaml'))
        assert dialog.cmbInputTemplate.count() > 3  # ComboBox should have items


    def test_model_accept_valid_data(self, model, temp_data_dir):
        """Test that the model accepts valid data."""
        configpath = str(Path(__file__).parent.parent / 'configs/base_spectra_config.yaml')
        templatepath = str(Path(__file__).parent.parent / 'n42Templates/rase_n42_template.n42')
        inputpath = str(Path(__file__).parent.parent / 'tests/example_template_conversion/in')
        outpath = str(Path(__file__).parent.parent / temp_data_dir)

        model.setData(model.fields['path_input_config'], configpath, Qt.EditRole)
        model.setData(model.fields['input_data_format'], 'rase_dummy', Qt.EditRole)
        model.setData(model.fields['path_output_template'], templatepath, Qt.EditRole)
        model.setData(model.fields['path_input_folder'], inputpath, Qt.EditRole)
        model.setData(model.fields['path_output_folder'], outpath, Qt.EditRole)

        failed_files = model.accept()
        assert failed_files == []  # No failed files

    def test_model_accept_invalid_data(self, model):
        """Test that the model raises an exception for invalid data."""
        model.setData(model.fields['path_input_config'], '', Qt.EditRole)  # Missing config path
        with pytest.raises(Exception, match='Exception: All fields must be filled'):
            model.accept()

    def test_dialog_accept_success(self, dialog, qtbot, temp_data_dir):
        """Test the dialog's accept method when succeeding."""
        from unittest.mock import patch
        configpath = str(Path(__file__).parent.parent / 'configs/base_spectra_config.yaml')
        templatepath = str(Path(__file__).parent.parent / 'n42Templates/rase_n42_template.n42')
        inputpath = str(Path(__file__).parent.parent / 'tests/example_template_conversion/in')
        outpath = str(Path(__file__).parent.parent / temp_data_dir)

        dialog.txtConfigPath.setText(configpath)
        dialog.cmbInputTemplate.setCurrentText('rase_dummy')
        dialog.txtTemplatePath.setText(templatepath)
        dialog.txtInputPath.setText(inputpath)
        dialog.txtOutputPath.setText(outpath)

        # Patch QMessageBox.information to prevent the popup
        with patch.object(QMessageBox, 'information') as mock_information:
            qtbot.mouseClick(dialog.buttonBox.button(dialog.buttonBox.StandardButton.Ok), Qt.LeftButton)
            mock_information.assert_called_once()
            args, kwargs = mock_information.call_args
            assert len(args) >= 2, 'QMessageBox.information was not called with the expected arguments.'
            completed_message = args[2]  # The actual text, should not have "failed" files
            assert completed_message == 'Processing completed. ', 'Unexpected completed_message content.'


    def test_dialog_accept_fail(self, dialog, qtbot, temp_data_dir):
        """Test the dialog's accept method when failing."""
        from unittest.mock import patch
        configpath = str(Path(__file__).parent.parent / 'configs/base_spectra_config.yaml')
        templatepath = str(Path(__file__).parent.parent / 'n42Templates/rase_n42_template.n42')
        inputpath = str(Path(__file__).parent.parent / 'tests/example_template_conversion/in')
        outpath = str(Path(__file__).parent.parent / temp_data_dir)

        dialog.txtConfigPath.setText(configpath)
        dialog.cmbInputTemplate.setCurrentText('SN11/23')
        dialog.txtTemplatePath.setText(templatepath)
        dialog.txtInputPath.setText(inputpath)
        dialog.txtOutputPath.setText(outpath)

        # Patch QMessageBox.information to prevent the popup
        with patch.object(QMessageBox, 'information') as mock_information:
            # Simulate clicking the OK button in the main dialog
            qtbot.mouseClick(dialog.buttonBox.button(dialog.buttonBox.StandardButton.Ok), Qt.LeftButton)
            # Assert QMessageBox.information was called
            mock_information.assert_called_once()
            # Extract the arguments passed to QMessageBox.information
            args, kwargs = mock_information.call_args
            assert len(args) >= 2, "QMessageBox.information was not called with the expected arguments."
            completed_message = args[2]  # The actual text, should not have "failed" files
            assert completed_message == ('Processing completed. Files not converted: \n\n  -- '
                                         'DUMMY_M001_Delta_Delta.n42'), 'Unexpected completed_message content.'


    def test_model_reset_data(self, model):
        """Test resetting the model data."""
        model.setData(model.fields["path_input_config"], "test_config.yaml", Qt.EditRole)
        model.reset_data()
        assert model.data(model.fields["path_input_config"]) != "test_config.yaml"  # Should reset


    def test_output(self, temp_data_dir):
        from src.spectrum_file_reading import readSpectrumFile
        from src.base_spectra_dialog import SharedObject

        origfolderpath = Path(__file__).parent.parent / 'tests/example_template_conversion/in'
        originputfile = Path('DUMMY_M001_Delta_Delta.n42')
        assert os.path.isfile(origfolderpath / originputfile)
        templatedfolderpath = Path(__file__).parent.parent / temp_data_dir
        templatedinputfile = Path('templated_DUMMY_M001_Delta_Delta.n42')
        assert os.path.isfile(templatedfolderpath / templatedinputfile)

        sharedObject = SharedObject(True)
        sharedObject.bkgndSpectrumInFile = True
        spec_data = []
        for spectrum_file in [origfolderpath / originputfile, templatedfolderpath / templatedinputfile]:
            spec_data.append(readSpectrumFile(spectrum_file, sharedObject=sharedObject, tstatus='', requireRASESen=False))

        assert spec_data[1][4] is None
        assert spec_data[1][5] is None
        for i in range(len(spec_data[0])):
            # 2 = foreground realtime (template does not allow foreground realtime to differ from livetime)
            # 5 = rase sensitivity factor (not included in template, should be NaN)
            # 6 = flux sensitivity factor (not included in template, should be NaN)
            assert spec_data[0][i] == spec_data[1][i] if i not in [2, 4, 5] else True

        # cleanup; TODO: is there a better way to invoke cleanup?
        os.remove(templatedfolderpath / templatedinputfile)


class Test_Results_Removal:
    """
    Make sure the results removal functionality works as expected
    Does not test GUI, but the GUI is so simple I don't think it's worth testing
    """
    hoc = HelpObjectCreation()

    def test_strip(self, temp_data_dir):
        # required arguments
        in_dir = Path(__file__).parent / '..' / 'tests' / 'example_remove_results'
        out_dir = Path(temp_data_dir) / 'out'

        # clear old results, just in case they are lingering for some reason
        try:
            shutil.rmtree(out_dir)
        except FileNotFoundError:
            pass

        n_converted, n_copied = remove_xmlblock(in_dir, out_dir)
        # check to see how many files have been created (should be 4)
        assert n_converted == 2
        assert n_copied == 1
        assert len([item for item in out_dir.iterdir() if item.is_file()]) == 4
        shutil.rmtree(out_dir)

        # what if we include the Am241.txt file
        additional_suffixes = ['*.txt', '*.TXT']  # search for files with these suffixes in addition to the default
        n_converted, n_copied = remove_xmlblock(in_dir, out_dir, additional_suffixes=additional_suffixes)
        assert n_converted == 3
        assert n_copied == 1
        assert len([item for item in out_dir.iterdir() if item.is_file()]) == 5

        # all cases should have analysis results in the input dir and no analysis results in the output dir
        for filename in ['VGeneric_MNaI2x2_Co60.n42', 'VGeneric_MNaI2x2_Ba133.n42', 'VGeneric_MNaI2x2_Am241.txt']:
            tree = etree.parse(in_dir / filename)
            root = tree.getroot()
            assert root.find('{*}AnalysisResults') is not None
            tree = etree.parse(out_dir / filename)
            root = tree.getroot()
            assert root.find('{*}AnalysisResults') is None

        # both backgrounds should have no AnalysisResults
        filename = 'VGeneric_MNaI2x2_Bgnd.n42'
        for testdir in [in_dir, out_dir]:
            tree = etree.parse(testdir / filename)
            root = tree.getroot()
            assert root.find('{*}AnalysisResults') is None

        # make sure logfile has been created and says what we expect
        logfile = out_dir / 'AnalysisResults_not_present.txt'
        assert logfile.is_file()
        with logfile.open('r') as f:
            assert f.readline() == 'VGeneric_MNaI2x2_Bgnd.n42\n'
        shutil.rmtree(out_dir)

        # make sure the "no log creation" and "no copy of unmodified files" capabilities work
        n_converted, n_copied = remove_xmlblock(in_dir, out_dir, copy_unmodified=False, log_noanalysis_files=False)
        # check to see how many files have been created: should only be Co60 and Ba133
        assert n_converted == 2
        assert n_copied == 0
        assert len([item for item in out_dir.iterdir() if item.is_file()]) == 2
        shutil.rmtree(out_dir)


from src.base_spectra_dialog import BaseSpectraLoadModel
class Test_Model_View:

    def test_create_detector(self, dummy_base_spectrum, temp_data_dir):
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
