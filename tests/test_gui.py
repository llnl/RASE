import os
from pathlib import Path

import pytest
from src.qt_utils import qt_install_translator, get_lang
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from src.rase import Rase
from src.replay_dialog import ReplayDialog
from src.table_def import Detector, Replay, Scenario, Session
from src.view_results_dialog import ViewResultsDialog

from tests.fixtures import HelpObjectCreation, db_and_output_folder, temp_data_dir


def screenshot(widget, folder=f"{Path(__file__).parent / '../tests/screenshots'}"):
    lang = get_lang()
    out_folder = Path(folder) / Path(lang)
    os.makedirs(out_folder, exist_ok=True)
    pixmap = widget.grab()
    parts = ["screenshot", ]
    name = widget.objectName()
    parts.append(name if name else widget.__class__.__name__)
    path = out_folder / ("_".join(parts) + ".png")
    pixmap.save(str(path))
    return path

class TestGUIScreenshots:
    @pytest.fixture
    def rase_main(self, qtbot):
        qt_install_translator()
        w = Rase([])
        w.show()
        qtbot.addWidget(w)
        qtbot.waitExposed(w)
        assert w.isVisible()
        return w

    @staticmethod
    def close_dialog(name):
        # this works even for dialogs that are not children of rase_main
        for child in QApplication.instance().topLevelWidgets():
            if child.objectName() == name:
                dialog = child
                assert dialog
                screenshot(dialog)
                dialog.close()
                dialog.deleteLater()

    def test_main_window(self, qtbot, rase_main):
        assert rase_main.isVisible()
        screenshot(rase_main)

    def test_about_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('AboutDialog'))
        rase_main.actionAbout.trigger()

    def test_preferences_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('PreferencesDialog'))
        rase_main.actionPreferences.trigger()

    def test_add_detector_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('AddDetectorDialog'))
        qtbot.mouseClick(rase_main.btnAddDetector, Qt.LeftButton)

    def test_create_scenario_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('ScenarioDialog'))
        qtbot.mouseClick(rase_main.btnAddScenario, Qt.LeftButton)

    def test_base_spectra_creation_tool_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('CreateBaseSpectraDialog'))
        rase_main.actionBase_Spectra_Creation_Tool.trigger()

    def test_correspondence_table_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('CorrTableDialog'))
        rase_main.actionCorrespondence_Table.trigger()

    def test_auto_scurve_dialog(self, qtbot, rase_main):
        hoc = HelpObjectCreation()
        hoc.create_default_corr_table()
        QTimer.singleShot(500, lambda: self.close_dialog('AutoSCurveDialog'))
        rase_main.actionAutomated_Scurve.trigger()

    def test_create_shielded_base_spectra_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('CreateShieldedBaseSpectraDialog'))
        rase_main.actionShielded_Base_Spectra_Creation.trigger()

    def test_manage_replays_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('ManageReplaysDialog'))
        rase_main.actionReplay_Software.trigger()

    def test_replay_dialog(self, qtbot, rase_main):
        QTimer.singleShot(500, lambda: self.close_dialog('ReplayDialog'))
        dialog = ReplayDialog(rase_main)
        dialog.exec()

    def test_results_dialog(self, qtbot, rase_main):
        from src.contexts import SimContext
        hoc = HelpObjectCreation()
        hoc.create_default_corr_table()
        hoc.create_default_detector_scen()
        s_context = [SimContext(Session().query(Detector).first(), Session().query(Replay).first(), Scenario())]
        QTimer.singleShot(500, lambda: self.close_dialog('ResultsDialog'))
        dialog = ViewResultsDialog(rase_main, s_context)
        dialog.exec()

