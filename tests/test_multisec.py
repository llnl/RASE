import sys
from time import sleep

import pytest
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import QDialogButtonBox, QMenu, QApplication, QMessageBox, QDialog

from src.replay_dialog import ReplayDialog
from src.base_spectra_dialog import BaseSpectraDialog
from src.detector_dialog import DetectorDialog
from src.scenario_dialog import ScenarioDialog
from src.rase import Rase
from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.scenario_group_dialog import GroupSettings as gsd
from sqlalchemy.orm import close_all_sessions


from .fixtures import (temp_data_dir, db_and_output_folder, generic_nai_spectra, dummy_base_spectrum,
                       HelpObjectCreation, Helper, example_multisec_base)





@pytest.fixture(scope='class')
def base_import_window():
    w = BaseSpectraDialog()
    return w

@pytest.fixture(scope='session')
def main_window():
    w = Rase(None)
    return w


class Helper(QObject):
    finished = Signal()


# GUI testing
class Test_Load_spectra:
    def test_load_dir(self,qtbot, base_import_window, example_multisec_base ):
        w = base_import_window
        w.show()
        qtbot.addWidget(w)
        w.on_btnBrowse_clicked(False,
                              example_multisec_base,
                               secType='Background Spectrum'
                              )
        w.accept()

    def test_detector_dialog(self,qtbot, base_import_window):
        print('testing-----------', flush=True)
        session = Session()
        w = base_import_window

        dd = DetectorDialog(None)
        dd.show()
        qtbot.addWidget(dd)
        qtbot.keyClicks(dd.txtDetector, 'test_detector'+'\t') # triggers handleEditingFinished()
        # dd.txtDetector.setText('test_detector')
        # dd.handleEditingFinished()
        dd.on_btnAddBaseSpectra_clicked(False,w)
        dd.secondaryIsBackgroundRadio.setChecked(True)
        dd.combo_typesecondary.setCurrentIndex(secondary_type['file'])
        dd.combo_basesecondary.setCurrentText('Background')
        qtbot.wait(30)

        replaydialog = ReplayDialog(dd)
        replaydialog.txtName.setText('testreplay')
        replaydialog.txtTemplatePath.setText(
            str(Path(__file__).parent/'../n42Templates/example_multisecondary_template.n42'))
        replaydialog.accept()
        dd.on_btnNewReplay_clicked(False, replaydialog) #added replay, not yet checkboxed
        checkbox_index = dd.tblViewReplay.model().index(0,0)
        dd.tblViewReplay.setCurrentIndex(checkbox_index)
        qtbot.keyPress(dd.tblViewReplay, Qt.Key_Space)
        # dd.model.set_replay('testreplay')


        dd.accept()
        assert dd.detector.replays
        assert dd.detector.replays[0].name == 'testreplay'
        saved_det = session.query(Detector).filter_by(name='test_detector').one()
        assert len(saved_det.secondary_spectra)==2
        assert saved_det.bckg_spectrum.livetime >300

        #TODO: test delete spectra

    def test_detector_reopen(self,qtbot,):
        session = Session()

        dd = DetectorDialog(None,'test_detector')
        dd.combo_typesecondary.setCurrentIndex(secondary_type['base_spec'])
        dd.accept()

        dd = DetectorDialog(None, 'test_detector')
        dd.combo_typesecondary.setCurrentIndex(secondary_type['file'])
        dd.accept()

    def test_scenario_creation(self, qtbot, main_window):
        w = ScenarioDialog(main_window)
        w.show()
        # comboSelectMaterial = w.tblMaterial.itemDelegate().createEditor()
        item = w.tblMaterial.model().index(0,1)
        assert item is not None
        rect = w.tblMaterial.visualRect(item)
        qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
        qtbot.mouseDClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
        qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())

        cell = w.tblMaterial.model().index(0,1)
        w.tblMaterial.setCurrentIndex(cell)
        qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
        qtbot.keyClicks(w.tblMaterial, 'Co60') # types in just enough to select the drop down item
        qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
        w.accept()
        main_window.populateScenarios()
        main_window.populateScenarioGroupCombo()
        assert main_window.tblScenario.rowCount() == 1
        assert main_window.tblScenario.item(0,1).text() == 'Co60-multisec(0.1)'

    def test_run_generation(self,qtbot, main_window):
        w = main_window
        w.show()
        scenitem = w.tblScenario.item(0, 0)
        scenrect = w.tblScenario.visualItemRect(scenitem)
        detitem = w.tblDetectorReplay.item(0, 0)
        detrect = w.tblDetectorReplay.visualItemRect(detitem)

        qtbot.mouseClick(w.tblDetectorReplay.viewport(), Qt.LeftButton, pos=detrect.center())
        qtbot.mouseClick(w.tblScenario.viewport(), Qt.LeftButton, pos=scenrect.center())
        assert(main_window.btnGenerate.isEnabled())

        def handle_ok(w, qtbot):
            messagebox = w.findChild(QMessageBox)
            ok_button = messagebox.button(QMessageBox.Ok)
            qtbot.mouseClick(ok_button, Qt.LeftButton, delay=1)

        QTimer.singleShot(3000, lambda: handle_ok(w, qtbot))
        assert main_window.on_btnGenerate_clicked(False)
    #
    # def test_paths_dialog(self,qtbot):
    #     w = DynamicPathsDialog()
    #     w.addPath(name="testpath")
    #     w.displayPath(w.listmodel.index(0), None)
    #     w.enableModification()
    #     w.model.setData(w.model.index(1,0), 100, Qt.EditRole)
    #     w.model.setData(w.model.index(1, 3), 20, Qt.EditRole)
    #     w.savePathChanges()
    #
    # def test_scenario_creation(self,qtbot, main_window_dy):
    #     w = DynamicScenarioDialog(main_window_dy)
    #     w.show()
    #     # comboSelectMaterial = w.tblMaterial.itemDelegate().createEditor()
    #     item = w.tblMaterial.item(0, 1)
    #     assert item is not None
    #     rect = w.tblMaterial.visualItemRect(item)
    #     qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
    #     qtbot.mouseDClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
    #     qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
    #     cell = w.tblMaterial.cellWidget(0,1)
    #     qtbot.keyClicks(cell, 'Cs137')
    #     qtbot.mouseClick(w.tblMaterial.viewport(), Qt.LeftButton, pos=rect.center())
    #     qtbot.keyClicks(w.txtSampleHz,'10')
    #     w.accept()
    #     main_window_dy.populateScenarios()
    #     main_window_dy.populateScenarioGroupCombo()
    #     testscen = Session.query(DynamicScenario).one_or_none()
    #
    # def test_run_generation(self,qtbot, main_window_dy):
    #     w = main_window_dy
    #     w.show()
    #     scenitem = w.tblScenario.item(0, 0)
    #     scenrect = w.tblScenario.visualItemRect(scenitem)
    #     detitem = w.tblDetectorReplay.item(0, 0)
    #     detrect = w.tblDetectorReplay.visualItemRect(detitem)
    #
    #     qtbot.mouseClick(w.tblDetectorReplay.viewport(), Qt.LeftButton, pos=detrect.center())
    #     qtbot.mouseClick(w.tblScenario.viewport(), Qt.LeftButton, pos=scenrect.center())
    #     assert(main_window_dy.btnGenerate_dy.isEnabled())
    #     main_window_dy.on_btnGenerate_dy_clicked(False)

