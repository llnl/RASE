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
"""
This module defines the main UI of RASE
"""

from matplotlib import rcParams
from itertools import product
import subprocess
import sys
import traceback

from PySide6.QtCore import QPoint, Qt, QSize, QObject, Slot, Signal
from PySide6.QtGui import QFont, QTextDocument, QAbstractTextDocumentLayout, QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMenu, \
    QMessageBox, QAbstractItemView, QStyledItemDelegate, QStyle, QFileDialog, \
    QHeaderView, QDialog, QProgressDialog, QCheckBox
from sqlalchemy.orm import make_transient
from sqlalchemy.sql import select

from src import rase_init
from src.automated_s_curve import generate_curve
from src.automated_s_curve_dialog import AutomatedSCurve
from src.correspondence_table_dialog import CorrespondenceTableDialog
from src.create_base_spectra_dialog import CreateBaseSpectraDialog
from src.create_base_spectra_wizard import CreateBaseSpectraWizard
from src.create_shielded_spectra_dialog import CreateShieldedSpectraDialog
from src.detector_dialog import DetectorDialog
from src.help_dialog import HelpDialog
from src.manage_influences_dialog import ManageInfluencesDialog
from src.manage_replays_dialog import ManageReplaysDialog
from src.manage_weights_dialog import ManageWeightsDialog
from src.plotting import SampleSpectraViewerDialog, MultiSpecViewerDialog
from src.progressbar_dialog import ProgressBar
from src.qt_utils import QSignalWait
from src.replay_dialog import ReplayDialog
from src.replay_generation import ReplayGeneration, TranslationGeneration
from src.random_seed_dialog import RandomSeedDialog
from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.scenario_dialog import ScenarioDialog
from src.scenario_group_dialog import GroupSettings
from src.settings_dialog import SettingsDialog
from src.contexts import SimContext
from src.spectra_generation import SampleSpectraGeneration
from src.table_def import Session, Detector, Scenario, Replay, ScenarioGroup, \
    ScenarioMaterial, scen_infl_assoc_tbl, CorrespondenceTable
from src.ui_generated import ui_rase, ui_about_dialog
from src.view_results_dialog import ViewResultsDialog


rcParams['backend'] = 'QtAgg'

SCENARIO_ID, MATER_EXPOS, BCKRND, INFLUENCES, ACQ_TIME, REPLICATION, COMMENT = range(7)
DETECTOR, REPLAY, REPL_SETTS = range(3)

# On Windows platforms, pass this startupinfo to avoid showing the console when running a process via popen
popen_startupinfo = None
if sys.platform.startswith("win"):
    popen_startupinfo = subprocess.STARTUPINFO()
    popen_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    popen_startupinfo.wShowWindow = subprocess.SW_HIDE

class Rase(ui_rase.Ui_MainWindow, QMainWindow):
    def __init__(self, args):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.setAcceptDrops(True)
        self.settings = RaseSettings()
        # random seed and "random seed fixed" boolean not retained across sessions
        self.settings.setRandomSeed(self.settings.getRandomSeedDefault())
        self.settings.setRandomSeedFixed(self.settings.getRandomSeedFixedDefault())
        self.settings.setUseConfidencesInCalcs(self.settings.getUseConfidencesInCalcs())
        self.settings.setUseMWeightsInCalcs(self.settings.getUseMWeightsInCalcs())
        self.help_dialog = None
        self.setFocusPolicy(Qt.StrongFocus)
        self._handled_exception = self.tr('Handled Exception')

        # change fonts if on Mac
        if sys.platform == 'darwin':
            font = QFont()
            font.setPointSize(12)
            self.tblScenario.setFont(font)
            self.tblDetectorReplay.setFont(font)

        # setup table properties
        self.tblScenario.setColumnCount(7)
        self.setTableHeaders()
        self.tblScenario.horizontalHeaderItem(MATER_EXPOS).setToolTip(r'Dose = (\u00B5Sv/h), <i>Flux = (\u03B3/('
                                                                       r'cm\u00B2s))<\i>')
        self.tblScenario.horizontalHeaderItem(BCKRND).setToolTip(r'Dose = (\u00B5Sv/h), <i>Flux = (\u03B3/('
                                                                       r'cm\u00B2s))<\i>')
        self.tblScenario.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblScenario.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tblScenario.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblScenario.setItemDelegate(HtmlDelegate())
        self.tblScenario.setSortingEnabled(True)
        self.tblScenario.horizontalHeader().setDefaultSectionSize(20)
        self.tblScenario.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tblScenario.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.tblDetectorReplay.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblDetectorReplay.setColumnCount(3)
        self.detectorHorizontalHeaderLabels = [self.tr('Instrument'), self.tr('Replay'), self.tr('Replay Settings')]
        self.tblDetectorReplay.setHorizontalHeaderLabels(self.detectorHorizontalHeaderLabels)
        self.tblDetectorReplay.setItemDelegate(HtmlDelegate())
        self.tblDetectorReplay.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tblDetectorReplay.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tblDetectorReplay.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tblDetectorReplay.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        rase_init.init_rase()
        self.populateAll()

        # connect selection changes to updating buttons and tables
        self.tblScenario.itemSelectionChanged.connect(self.updateDetectorColors)
        self.tblDetectorReplay.itemSelectionChanged.connect(self.updateScenarioColors)

        self.settings.setIsAfterCorrespondenceTableCall(self.settings.getIsAfterCorrespondenceTableCalldDefault())

        self.btnExportInstruments.clicked.connect(self.handleInstrumentExport)
        self.btnExportScenarios.clicked.connect(self.handleScenarioExport)
        self.btnImportScenariosXML.clicked.connect(lambda: self.handleScenarioImport('xml'))
        self.btnImportScenariosCSV.clicked.connect(lambda: self.handleScenarioImport('csv'))
        self.btnGenScenario.clicked.connect(self.genScenario)

        self.setImportButtonVisibile(False)
        self.ckboxEnableAdvanced.stateChanged.connect(self.setImportButtonVisibile)

    def closeEvent(self, event) -> None:
        Session().close()
        Session().bind.dispose()
        event.accept()


    @Slot(int)
    def setImportButtonVisibile(self, state=1):
        self.btnImportSpectra.setVisible(state)
        self.btnImportIDResults.setVisible(state)
        self.btnRunResultsTranslator.setVisible(state)

    def handleInstrumentExport(self):
        """
        Exports Instrument to CSV
        """
        path = QFileDialog.getSaveFileName(self, self.tr('Save File'), self.settings.getLastDirectory(), 'CSV (*.csv)')
        if path[0]:
            with open(path[0], mode='w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(self.detectorHorizontalHeaderLabels)
                for row in range(self.tblDetectorReplay.rowCount()):
                    rowdata = []
                    for column in range(self.tblDetectorReplay.columnCount()):
                        item = self.tblDetectorReplay.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

    def handleScenarioExport(self):
        """
        Exports Scenarios to XML
        """
        path = QFileDialog.getSaveFileName(self, self.tr('Save File'), self.settings.getLastDirectory(), 'XML (*.xml)')
        if path[0]:
            if len(self.tblScenario.selectedIndexes()) > 0:
                scenIds = self.getSelectedScenarioIds()
            else:
                scenIds = self.getAllScenarioIds()
            export_scenarios(scenIds, path[0])

    def handleScenarioImport(self, file_format):
        """
        Import Scenarios from different formats
        """
        files_filter = {'xml': 'XML (*.xml)', 'csv': 'CSV(*.csv)'}
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr('Open File'), self.settings.getLastDirectory(),
                                               files_filter[file_format])
        for path in paths:
            session = Session()
            try:
                # scenarios are imported within a group named after the file
                scenarios = import_scenarios(path, file_format,
                                             group_name=Path(path).with_suffix('').name, group_desc='Imported')
                session.add_all(scenarios)
            except Exception as e:
                traceback.print_exc()
                logging.exception(self._handled_exception, exc_info=True)
                QMessageBox.critical(self, self.tr('Import Failed'), self.tr('Failed to import '
                                                             'scenarios<br><br>{}').format(str(e)))
                session.rollback()
            else:
                session.commit()
                self.populateAll()

    def setTableHeaders(self):
        self.scenarioHorizontalHeaderLabels = [self.tr('ID'), self.tr('Sources'),
                                               self.tr('Backgrounds'), self.tr('Influences'),
                                               self.tr('AcqTime (s)'), self.tr('Replication'),
                                               self.tr('Comments')]
        self.tblScenario.setHorizontalHeaderLabels(self.scenarioHorizontalHeaderLabels)

    def populateAll(self):
        """
        Repopulate scenario, instrument/replay, and scenario-group combo. good to call after initializeDatabase
        """
        self.populateScenarios()
        self.populateDetectorReplays()
        self.populateScenarioGroupCombo()

    def populateScenarioGroupCombo(self):
        currentSelection = self.cmbScenarioGroups.currentText()
        self.cmbScenarioGroups.clear()
        self.cmbScenarioGroups.addItem(self.tr('All Scenario Groups'))
        check_groups()
        for scenGrp in Session().query(ScenarioGroup):
            self.cmbScenarioGroups.addItem(scenGrp.name)
        if currentSelection:
            self.cmbScenarioGroups.setCurrentText(currentSelection)

    def populateScenarios(self):
        """
        Shows scenarios in main screen scenario table
        Scenarios are filtered if there is a text search or group selected
        The text search is implemented as an OR between space-separated terms
        Text within quotes is kept as a single term
        """
        # Disable sorting while setting/inserting items to avoid crashes
        self.tblScenario.setSortingEnabled(False)

        session = Session()
        # select scenarios to display based on search criteria
        scenSearch = self.txtScenarioSearch.text().strip()
        if scenSearch:
            scenIds = set()
            connection = Session().get_bind().connect()
            # don't break terms withing double quotes
            search_terms = csv.reader([scenSearch], skipinitialspace=True, delimiter=' ')
            for searchStr in next(search_terms):
                # materials search
                stmt = select(ScenarioMaterial).where(ScenarioMaterial.material_name.ilike('%' + searchStr + '%'))
                scenIds |= {row.scenario_id for row in connection.execute(stmt)}

                # Background materials search
                stmt = select(ScenarioBackgroundMaterial).where(
                    ScenarioBackgroundMaterial.material_name.ilike('%' + searchStr + '%'))
                scenIds |= {row.scenario_id for row in connection.execute(stmt)}

                # influences search
                stmt = select(scen_infl_assoc_tbl).where(
                    scen_infl_assoc_tbl.c.influence_name.ilike('%' + searchStr + '%'))
                scenIds |= {row.scenario_id for row in connection.execute(stmt)}

                # scenario comment search
                stmt = select(Scenario).where(Scenario.comment.ilike('%' + searchStr + '%'))
                scenIds |= {row.id for row in connection.execute(stmt)}

            scenarios = {session.get(Scenario, scenId) for scenId in scenIds}
        else:
            scenarios = list(session.query(Scenario))

        # select scenarios based on scenario group
        if self.cmbScenarioGroups.currentIndex() > 0:
            scenGrpId = session.query(ScenarioGroup).filter_by(name=self.cmbScenarioGroups.currentText()).first()
            scenarios = [scenario for scenario in scenarios if scenGrpId in scenario.scenario_groups]

        self.tblScenario.setRowCount(len(scenarios))
        for row, scenario in enumerate(scenarios):
            self.tblScenario.setRowHeight(row, 22)

            item = QTableWidgetItem(scenario.id)
            item.setData(Qt.UserRole, scenario.id)
            self.tblScenario.setItem(row, SCENARIO_ID, item)
            matExp = [f'{scen_mat.material.name}({scen_mat.dose:.5g})' for scen_mat in scenario.scen_materials]
            self.tblScenario.setItem(row, MATER_EXPOS, QTableWidgetItem(', '.join(matExp)))
            # TODO place correct data in BCKRND column
            bckgMatExp = [f'{scen_mat.material.name}({scen_mat.dose:.5g})' for scen_mat in scenario.scen_bckg_materials]
            self.tblScenario.setItem(row, BCKRND, QTableWidgetItem(', '.join(bckgMatExp)))
            self.tblScenario.setItem(row, INFLUENCES,
                                     QTableWidgetItem(', '.join(infl.name for infl in scenario.influences)))
            self.tblScenario.setItem(row, ACQ_TIME, QTableWidgetItem(str(scenario.acq_time)))
            self.tblScenario.setItem(row, REPLICATION, QTableWidgetItem(str(scenario.replication)))
            if scenario.comment:
                item = QTableWidgetItem(scenario.comment)
                item.setToolTip(scenario.comment)
                self.tblScenario.setItem(row, COMMENT, item)
            else:
                self.tblScenario.setItem(row, COMMENT, QTableWidgetItem(''))

        # color and resize
        self.updateScenarioColors()
        self.tblScenario.resizeColumnsToContents()
        self.tblScenario.resizeRowsToContents()

        # Re-enable sorting
        self.tblScenario.setSortingEnabled(True)

    def set_tblDetectorReplay_row(self, row: int, detector_name: str, replay_name: str, replay_settings: str):
        self.tblDetectorReplay.setRowHeight(row, 22)
        item = QTableWidgetItem(detector_name)
        item.setData(Qt.UserRole, detector_name)
        self.tblDetectorReplay.setItem(row, DETECTOR, item)
        item = QTableWidgetItem(replay_name)
        item.setData(Qt.UserRole, replay_name)
        self.tblDetectorReplay.setItem(row, REPLAY, item)
        self.tblDetectorReplay.setItem(row, REPL_SETTS, QTableWidgetItem(replay_settings))

    def populateDetectorReplays(self):
        """shows scenarios in rase main screen scenario table"""
        # Disable sorting while setting/inserting items to avoid crashes
        self.tblDetectorReplay.setSortingEnabled(False)

        session = Session()
        detSearch = self.txtDetectorSearch.text().strip()
        if detSearch:
            detNames = set()
            connection = Session().get_bind().connect()
            search_terms = csv.reader([detSearch], skipinitialspace=True, delimiter=' ')
            for searchStr in next(search_terms):
                # detector name search
                # TODO: add ability to search inside replay tools name as well
                stmt = select(Detector).where(Detector.name.ilike('%' + searchStr + '%'))
                detNames |= {row.name for row in connection.execute(stmt)}

            detectors = {session.get(Detector, detName) for detName in detNames}
        else:
            detectors = list(session.query(Detector))

        self.tblDetectorReplay.setRowCount(0)
        for detector in detectors:
            if detector.replays:
                for replay in detector.replays:
                    self.tblDetectorReplay.insertRow(self.tblDetectorReplay.rowCount())
                    self.set_tblDetectorReplay_row(self.tblDetectorReplay.rowCount()-1, detector.name, replay.name, replay.settings_str_u())
            else:
                self.tblDetectorReplay.insertRow(self.tblDetectorReplay.rowCount())
                self.set_tblDetectorReplay_row(self.tblDetectorReplay.rowCount()-1, detector.name, "", "")

        self.updateDetectorColors()
        # self.tblDetectorReplay.resizeColumnsToContents()
        self.tblDetectorReplay.resizeRowsToContents()

        # Re-enable sorting
        self.tblDetectorReplay.setSortingEnabled(True)


    def updateDetectorColors(self):
        """
        Updates the colors of the detectors in the instrument list
        """
        session = Session()
        selScenarioIds = self.getSelectedScenarioIds()
        scenario = session.query(Scenario).filter_by(id=selScenarioIds[0]).first() if len(selScenarioIds) == 1 else None

        for row in range(self.tblDetectorReplay.rowCount()):
            item = self.tblDetectorReplay.item(row, DETECTOR)
            detTxt = item.data(Qt.UserRole)
            detector = session.query(Detector).filter_by(name=detTxt).first()
            replTxt = self.tblDetectorReplay.item(row, REPLAY).data(Qt.UserRole)
            replay = session.query(Replay).filter_by(name=replTxt).first()
            toolTip = ''

            detectorColor = 'black'
            procphase = ''
            for scenID in selScenarioIds:
                scenario = session.query(Scenario).filter_by(id=scenID).first()
                if files_exist(get_results_dir(self.settings.getSampleDirectory(), detector, replay, scenario.id)):
                    procphase = self.tr('Replay')
                    detectorColor = 'green'
                elif scenario and files_exist(get_sample_dir(
                        self.settings.getSampleDirectory(), detector, scenario.id)) and detectorColor != 'green':
                    detectorColor = 'orange'
                    procphase = self.tr('Spectrum generation')

            if len(selScenarioIds) != 0 and detectorColor != 'black':
                detTxt = '<font color=' + detectorColor + '>' + detector.name + '</font>'
                if len(selScenarioIds) == 1:
                    toolTip = self.tr('\n{} results available for {} and scenario {}').format(
                                                        procphase, detector.name, scenario.id)
                else:
                    toolTip = self.tr('\n{} results available for {} and selected scenarios').format(
                                                        procphase, detector.name)

            item.setText(detTxt)
            item.setToolTip(self.tr('Detector ID: {}{}').format(detector.id, toolTip))

            # replay
            if replay:
                replTxt = replay.name
                toolTip = None
                item = self.tblDetectorReplay.item(row, REPLAY)
                if replay and replay.is_runnable():
                    replTxt = '<font color="green">' + replay.name + '</font>'
                    toolTip = self.tr('Cmd line replay tool available for {}').format(detector.name)
                item.setText(replTxt)
                item.setToolTip(toolTip)

        self.updateActionButtons()

    def updateScenarioColors(self):
        """
        Updates the colors of all the scenarios
        """
        self.tblScenario.setSortingEnabled(False)
        session = Session()
        selDetectorNames = self.getSelectedDetectorNames()
        selReplayNames = self.getSelectedReplayNames()

        detectors = []
        replays = []
        det_infl = {}

        for detector_name, replay_name in zip(selDetectorNames, selReplayNames):
            detector = session.query(Detector).filter_by(name=detector_name).first()
            replay = session.query(Replay).filter_by(name=replay_name).first()
            if detector and replay:
                detectors.append(detector)
                replays.append(replay)
                det_infl[detector_name] = [detInfluence.name for detInfluence in detector.influences]

        for row in range(self.tblScenario.rowCount()):

            s_item = self.tblScenario.item(row, SCENARIO_ID)
            scenario = session.get(Scenario, s_item.data(Qt.UserRole))
            mat_toolTip = []
            inf_toolTip = []
            s_toolTip = []

            if not selDetectorNames:
                for (col, scenario_material) in [(MATER_EXPOS, scenario.scen_materials), (BCKRND, scenario.scen_bckg_materials)]:
                    item = self.tblScenario.item(row, col)
                    txtExp = []
                    for index, scenMat in enumerate(scenario_material):
                        if scenMat.fd_mode == 'DOSE':
                            scenExpTxt = (f'{scenMat.material_name}({scenMat.dose:.5g})')
                        else:
                            scenExpTxt = ('<i>' + f'{scenMat.material_name}({scenMat.dose:.5g})' + '</i>')
                        txtExp.append(scenExpTxt)
                    item.setText(', '.join(txtExp))
                    item.setToolTip('')

                item = self.tblScenario.item(row, INFLUENCES)
                txtExp = []
                for index, scenInfluence in enumerate(scenario.influences):
                    scenExpTxt = scenInfluence.name
                    txtExp.append(scenExpTxt)
                item.setText(', '.join(txtExp))
                item.setToolTip('')

                scenTxt = scenario.id
                s_item.setText(scenTxt)
                s_item.setToolTip('')

            else:
                # set materials/exposure
                det_missing_mat = set()
                mat_missing_det = set()
                for col, scenario_materials in zip([MATER_EXPOS, BCKRND],
                                          [scenario.scen_materials, scenario.scen_bckg_materials]):
                    item_text = []
                    item = self.tblScenario.item(row, col)

                    for scen_mat in set(scenario_materials):
                        for detector in detectors:
                            if not detector.scenariomaterial_is_allowed(scen_mat):
                                det_missing_mat.update([detector.name])
                                mat_missing_det.update([scen_mat])
                        if scen_mat in mat_missing_det:
                            mat_text = '<font color="red">' + scen_mat.material.name + '</font>'
                        else:
                            mat_text = scen_mat.material.name
                        if scen_mat.fd_mode == 'DOSE':
                            item_text.append(f'{mat_text}({scen_mat.dose:.5g})')
                        else:
                            item_text.append('<i>' + f'{mat_text}({scen_mat.dose:.5g})' + '</i>')
                    item.setText(', '.join(item_text))

                for detector_name in det_missing_mat:
                    mat_toolTip.append(self.tr('{} is missing base spectra for this scenario').format(detector_name))
                    s_toolTip.append(self.tr('{} is missing base spectra for this scenario').format(detector_name))
                for col in [MATER_EXPOS, BCKRND]:
                    item = self.tblScenario.item(row, col)
                    item.setToolTip(',\n'.join(mat_toolTip))


                # set influences
                det_missing_infl = set()
                infl_missing_det = set()
                item_text = []
                item = self.tblScenario.item(row, INFLUENCES)

                scen_infl = set(influence.name for influence in scenario.influences)
                for infl in scen_infl:
                    for detector_name in det_infl.keys():
                        if infl not in det_infl[detector_name]:
                            det_missing_infl.update([detector_name])
                            infl_missing_det.update([infl])
                    if infl in infl_missing_det:
                        item_text.append('<font color="red">' + infl + '</font>')
                    else:
                        item_text.append(infl)

                for detector_name in det_missing_infl:
                    inf_toolTip.append(self.tr('{} is missing influences for this scenario').format(detector_name))
                    s_toolTip.append(self.tr('{} is missing influences for this scenario').format(detector_name))
                item.setText(', '.join(item_text))
                item.setToolTip(',\n'.join(inf_toolTip))


                # set scenarios
                det_results = set()
                det_spectra = set()
                for detector, replay in zip(detectors, replays):
                    if files_exist(get_results_dir(self.settings.getSampleDirectory(), detector, replay, scenario.id)):
                        det_results.update([detector.name])

                    if files_exist(get_sample_dir(self.settings.getSampleDirectory(), detector, scenario.id)):
                        det_spectra.update([detector.name])

                for detector_name in det_results:
                    s_toolTip.append(self.tr('Identification results available for {} and this scenario').format(detector_name))
                for detector_name in det_spectra:
                    s_toolTip.append(self.tr('Sample spectra available for {} and this scenario').format(detector_name))

                if len(det_results) > 0:
                    scenTxt = '<font color="green">' + scenario.id + '</font>'
                elif len(det_spectra) > 0:
                    scenTxt = '<font color="orange">' + scenario.id + '</font>'
                elif len(det_missing_infl) + len(det_missing_mat) > 0:
                    scenTxt = '<font color="red">' + scenario.id + '</font>'
                else:
                    scenTxt = scenario.id
                s_item.setText(scenTxt)
                s_item.setToolTip(',\n'.join(s_toolTip))

        self.updateActionButtons()

        self.tblScenario.setSortingEnabled(True)

    def updateActionButtons(self):
        """
        Handles enabling and disabling of Action Buttons
        """
        scenIds = self.getSelectedScenarioIds()
        selDetectorNames = self.getSelectedDetectorNames()
        selReplayNames = self.getSelectedReplayNames()

        # clear buttons
        buttons = [self.btnGenScenario, self.btnGenerate, self.btnRunReplay, self.btnViewResults,
                   self.btnRunResultsTranslator, self.btnImportIDResults, self.btnImportSpectra]
        for button in buttons: button.setEnabled(False)
        if not (len(scenIds) and len(selDetectorNames)):
            [button.setToolTip(self.tr('Must choose scenario and instrument')) for button in buttons]
            return
        for button in buttons: button.setToolTip('')

        session = Session()

        replay_defined = []
        replay_commandline = []
        results_translators_defined = []
        samplesExists = []
        replayInputSamplesExists = []
        replayOutputExists = []
        resultsExists = []
        detMissingSpectra = []
        detMissingInfluence = []
        for detector_name, replay_name in zip(selDetectorNames, selReplayNames):

            detector = session.query(Detector).filter_by(name=detector_name).first()
            replay = session.query(Replay).filter_by(name=replay_name).first()

            if detector:
                replay_defined.append((replay and replay.is_defined()))
                replay_commandline.append((replay and replay.is_runnable()))
                if replay and replay.translator_exe_path:  # not all replay tools require a translator
                    results_translators_defined.append((replay.translator_exe_path
                                                       and replay.translator_is_cmd_line))

                det_infl = set(detInfl.name for detInfl in detector.influences)

                for scenId in scenIds:
                    scenario = session.query(Scenario).filter_by(id=scenId).first()
                    if scenario:
                        for scen_mat in set(scenario.scen_materials + scenario.scen_bckg_materials):
                            if not detector.scenariomaterial_is_allowed(scen_mat):
                                detMissingSpectra.append(scenId)

                        scen_infl = set(influence.name for influence in scenario.influences)
                        if not scen_infl <= det_infl: detMissingInfluence.append(scenId)

                        samplesExists.append(
                            files_exist(get_sample_dir(self.settings.getSampleDirectory(), detector, scenId)))
                        replayInputSamplesExists.append(
                            files_exist(get_replay_input_dir(self.settings.getSampleDirectory(), detector, replay, scenId)))
                        # Replay tool output files and results files are expected to end in ".n42" or ".res".
                        # Check explicitly in case other output is present (e.g. from replay tool or translator)
                        output_dir = get_replay_output_dir(self.settings.getSampleDirectory(), detector, replay, scenId)
                        if replay:
                            replayOutputExists.append(files_endswith_exists(output_dir, allowed_results_file_exts + (replay.input_filename_suffix,)))
                        else:
                            replayOutputExists.append(files_endswith_exists(output_dir, allowed_results_file_exts))
                        results_dir = get_results_dir(self.settings.getSampleDirectory(), detector, replay, scenId)
                        resultsExists.append(files_endswith_exists(results_dir, allowed_results_file_exts))

        if detMissingSpectra or detMissingInfluence:
            # generate sample is possible only if no missing base spectra or influences
            missingScenarios = missingInfluences = ''
            if detMissingSpectra:
                missingScenarios = self.tr('Missing base spectra for scenarios:') + '<br>' + '<br>'.join(detMissingSpectra)
            if detMissingInfluence:
                missingInfluences = self.tr('<br>Missing influences for scenarios:') + '<br>' + '<br>'.join(detMissingInfluence)

        # Run scenario button
        if detMissingSpectra or detMissingInfluence:
            self.btnGenScenario.setEnabled(False)
            self.btnGenScenario.setToolTip(missingScenarios + missingInfluences)
        elif not all(replay_commandline):
            self.btnGenScenario.setEnabled(False)
            self.btnGenScenario.setToolTip(self.tr('Command-line replay tool undefined for one or more instruments'))
        else:
            self.btnGenScenario.setEnabled(True)
            self.btnGenScenario.setToolTip('')

        # generate samples button
        if detMissingSpectra or detMissingInfluence:
            self.btnGenerate.setEnabled(False)
            self.btnGenerate.setToolTip(missingScenarios + missingInfluences)
        else:
            self.btnGenerate.setEnabled(True)
            self.btnGenerate.setToolTip('')

        # run replay button:
        if not any(replayInputSamplesExists):
            self.btnRunReplay.setEnabled(False)
            self.btnRunReplay.setToolTip(self.tr('Sample spectra have not yet been generated, translated or imported'))
        # FIXME: the following does not consider the case of a replay tool not from the command line
        elif not any(replay_defined):
            self.btnRunReplay.setEnabled(False)
            self.btnRunReplay.setToolTip(self.tr('No replay tool defined'))
        else:
            self.btnRunReplay.setEnabled(True)
            self.btnRunReplay.setToolTip('')

        # import results button and import sample spectra button:
        if len(selDetectorNames) == 1 and len(scenIds) == 1:
            self.btnImportIDResults.setEnabled(True)
            self.btnImportSpectra.setEnabled(True)
            self.btnImportIDResults.setToolTip('')
            self.btnImportSpectra.setToolTip('')
        else:
            self.btnImportSpectra.setEnabled(False)
            self.btnImportIDResults.setEnabled(False)
            self.btnImportSpectra.setToolTip(self.tr('Can only import one scenario at a time'))
            self.btnImportIDResults.setToolTip(self.tr('Can only import one scenario at a time'))

        # run results translator button:
        if not (results_translators_defined and any(results_translators_defined)):
            self.btnRunResultsTranslator.setEnabled(False)
            self.btnRunResultsTranslator.setToolTip(self.tr('No instruments have a command-line results translator defined '))
        elif not any(replayOutputExists):
            self.btnRunResultsTranslator.setEnabled(False)
            self.btnRunResultsTranslator.setToolTip(self.tr('All scenarios are missing replay tool output'))
        else:
            self.btnRunResultsTranslator.setEnabled(True)
            self.btnRunResultsTranslator.setToolTip('')

        # view results button
        if any(resultsExists):
            self.btnViewResults.setEnabled(True)
            self.btnViewResults.setToolTip(self.tr('Results are available'))
        else:
            self.btnViewResults.setEnabled(False)
            self.btnViewResults.setToolTip(self.tr('No results available'))

    def getSelectedScenarioIds(self):
        """
        :return: selected scenario ids
        """
        return [self.tblScenario.item(row, SCENARIO_ID).data(Qt.UserRole)
                for row in set(index.row() for index in self.tblScenario.selectedIndexes())]

    def getAllScenarioIds(self):
        """
        :return: all scenarios ids currently listed in the scenario table
        """
        return [self.tblScenario.item(row, SCENARIO_ID).data(Qt.UserRole) for row in range(self.tblScenario.rowCount())]

    def getSelectedDetectorNames(self):
        """
        :return: Selected Instrument Names
        """
        return [self.tblDetectorReplay.item(row, DETECTOR).data(Qt.UserRole)
                for row in set(index.row() for index in self.tblDetectorReplay.selectedIndexes())]

    def getSelectedReplayNames(self):
        """
        :return: Selected Replay Names
        """
        return [self.tblDetectorReplay.item(row, REPLAY).data(Qt.UserRole)
                for row in set(index.row() for index in self.tblDetectorReplay.selectedIndexes())]

    @Slot(int, int)
    def on_tblScenario_cellDoubleClicked(self, row, col):
        """
        Listens for Scenario cell double click and launches edit_scenario()
        """
        id = strip_xml_tag(self.tblScenario.item(row, SCENARIO_ID).text())
        self.edit_scenario(id)

    def edit_scenario(self, id):
        """
        Launcehes ScenarionDialog
        """
        dialog = ScenarioDialog(self, id)
        if dialog.exec_():
            self.populateScenarios()
        self.populateScenarioGroupCombo()

    def edit_detector(self, detectorName):
        """
        Launches Instrument Dialog
        """
        self.d_dialog = DetectorDialog(self, detectorName)  # attribute of RASE for testing purposes
        if self.d_dialog.exec_():
            self.populateDetectorReplays()
        self.d_dialog = None

    def clone_detector(self, detector_name: str) -> None:
        """
        Clone the detector with all its settings
        """
        session = Session()
        detector = session.query(Detector).filter_by(name=detector_name).first()
        influences = detector.influences
        spectra = detector.base_spectra
        spectra_xyz = detector.base_spectra_xyz
        bckg_spectra = detector.bckg_spectra
        secondary_spectra = detector.secondary_spectra
        make_transient(detector)
        detector.id = None  # new primary_key will be created on commit
        new_name = detector.name + self.tr(' (copy)')
        repeat_clone = 0
        while new_name in [d.name for d in session.query(Detector).all()]:
            repeat_clone += 1
            new_name = detector.name + self.tr(' (copy) {}').format(repeat_clone)
        detector.name = new_name
        session.add(detector)
        session.commit()

        # Now clone the attributes from related tables
        detector = session.query(Detector).filter_by(name=new_name).first()
        obj_dict = {'base_spectra': spectra,
                    'base_spectra_xyz': spectra_xyz,
                    'bckg_spectra': bckg_spectra,
                    'secondary_spectra': secondary_spectra}
        for attr, spectra_list in obj_dict.items():
            for s in spectra_list:
                if s.spectrum_type not in ['secondary_spectrum', 'background_spectrum']:
                    assert s.filename  # some lazy loading requires this
                make_transient(s)
                s.id = None
                getattr(detector, attr).append(s)
        detector.influences = influences
        session.commit()

        self.populateDetectorReplays()

    def duplicate_scen(self, id):
        dialog = ScenarioDialog(self, id, duplicate_ids=self.getSelectedScenarioIds())
        if dialog.exec_():
            self.populateScenarios()
        self.populateScenarioGroupCombo()

    def assign_to_group(self, scenids):
        session = Session()
        scens = [session.query(Scenario).filter_by(id=scenid).first() for scenid in scenids]
        groups = []
        for scen in scens:
            for group in scen.scenario_groups:
                if group.name not in groups:
                    groups.append(group.name)
        dialog = GroupSettings(self, groups, scens=scens)
        dialog.setWindowModality(Qt.WindowModal)
        if dialog.exec_():
            self.populateScenarios()
        self.populateScenarioGroupCombo()


    @Slot(int, int)
    def on_tblDetectorReplay_cellDoubleClicked(self, row, col):
        """
        Listens for Instrument or Replay cell click and launches corresponding edit dialogs
        """
        if col == DETECTOR:
            detectorName = strip_xml_tag(self.tblDetectorReplay.item(row, col).text())
            self.edit_detector(detectorName)
        elif col == REPLAY:
            session = Session()
            if self.tblDetectorReplay.item(row, col):
                replay = session.query(Replay).filter_by(
                    name=self.tblDetectorReplay.item(row, col).data(Qt.UserRole)).first()
                all_replays = [r for r in session.query(Replay).all()]
                if ReplayDialog(self, replay).exec():
                    all_replays_post = [r for r in session.query(Replay).all()]
                    if len(all_replays) != len(all_replays_post):   # new replay added
                        new_replay = [r for r in all_replays_post if r not in all_replays]
                        print(new_replay)
                        detectorName = strip_xml_tag(self.tblDetectorReplay.item(row, DETECTOR).text())
                        detector = session.query(Detector).filter_by(name=detectorName).first()
                        detector.add_replay(new_replay[0])
                        session.commit()
                self.populateDetectorReplays()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete or e.key() == Qt.Key_Backspace:
            scenIds = self.getSelectedScenarioIds()
            self.tblScenario.clearSelection()
            self.tblDetectorReplay.clearSelection()
            delete_scenario(scenIds, self.settings.getSampleDirectory())
            self.populateAll()

    # def focusInEvent(self, e):
    #     self.updateDetectorColors()
    #     self.updateScenarioColors()
    #     self.updateActionButtons()

    @Slot(QPoint)
    def on_tblDetectorReplay_customContextMenuRequested(self, point):
        """
        Handles "Edit" and "Delete" right click selections on the Instrument table
        """
        current_cell = self.tblDetectorReplay.itemAt(point)
        # show the context menu only if on an a valid part of the table
        if current_cell:
            row = current_cell.row()
            deleteAction = QAction(self.tr('Delete Instrument'), self)
            editAction = QAction(self.tr('Edit Instrument'), self)
            cloneAction = QAction(self.tr('Clone Instrument'), self)
            menu = QMenu(self.tblDetectorReplay)
            menu.addAction(deleteAction)
            menu.addAction(editAction)
            menu.addAction(cloneAction)
            action = menu.exec_(self.tblDetectorReplay.mapToGlobal(point))
            session = Session()
            name = strip_xml_tag(self.tblDetectorReplay.item(row, 0).text())
            if action == deleteAction:
                if len(self.getSelectedScenarioIds()):
                    QMessageBox.critical(self, self.tr('Scenario Selected'),
                                 self.tr('Please Unselect All Scenarios Prior to Deleting Instrument'))
                    return
                confirm = QMessageBox.question(self, self.tr('Confirm Instrument Deletion'),
                                               self.tr('Are you sure you want to delete this instrument?\n\n'
                                               'Any generated spectra or results with this instrument may be lost.'),
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm == QMessageBox.StandardButton.Yes:
                    delete_instrument(session, name)
                self.populateAll()
            elif action == editAction:
                self.edit_detector(name)
            elif action == cloneAction:
                self.clone_detector(name)

    @Slot()
    def genScenario(self):
        """
        Launches a single button to do all processing (generate, replay, and translate)
        """
        replay_status = False
        sim_context_list = self.runSelect()
        spec_status = self.genSpectra(sim_context_list)
        if spec_status:
            replay_gui = ReplayGenerationGUI(self, sim_context_list, self.settings)
            replay_status = replay_gui.runReplay()
        self.on_action_complete(spec_status and replay_status, self.tr("Scenarios processing"))

    @Slot(bool)
    def on_btnGenerate_clicked(self, checked):
        status = self.genSpectra(self.runSelect())
        self.on_action_complete(status, self.tr("Sample spectra generation"))
        return status

    def runSelect(self) -> list[SimContext]:
        scenIds = self.getSelectedScenarioIds()
        detNames = self.getSelectedDetectorNames()
        repNames = self.getSelectedReplayNames()

        sim_context_list = []
        for (d, r), s in product(zip(detNames, repNames), scenIds):
            detector = Session().query(Detector).filter_by(name=d).first()
            replay = Session().query(Replay).filter_by(name=r).first()
            scenario = Session().query(Scenario).filter_by(id=s).first()
            sim_context_list.append(SimContext(detector=detector, replay=replay, scenario=scenario))
        return sim_context_list

    def genSpectra(self, sim_context_list: list[SimContext], dispProg=True, checked=False):
        """
        Launches generation of sample spectra
        """
        # get selected conditions
        session = Session()

        overwrite = False
        ill_defined_scen = 0

        # Check if any sample spectra may be overwritten
        # Loop over a copy of sim_context_list since the list is modified in the loop
        for sim_context in list(sim_context_list):
            detector = sim_context.detector
            scenario = sim_context.scenario
            replay = sim_context.replay
            directoryName = get_sample_dir(self.settings.getSampleDirectory(), detector, scenario.id)
            if files_exist(directoryName):
                if not checked:
                    answer = QMessageBox(QMessageBox.Question, self.tr('Sample spectra already exists'),
                                  self.tr('Sample spectra for instrument: {} and scenario: {} '
                                          'already exists. <br><br> Select yes to overwrite or no to skip '
                                          'this case. <br>This choice is automatically applied to all replay tools '
                                          'associated with this instrument.').format(detector.name, scenario.id))
                    answer.addButton(QMessageBox.Yes)
                    answer.addButton(QMessageBox.No)
                    checkit = QCheckBox(self.tr('Use this selection for all scenarios'))
                    checkit.setEnabled(True)
                    answer.setCheckBox(checkit)
                    ans_hold = answer.exec()
                    if ans_hold == QMessageBox.No:
                        sim_context_list[:] = [sc for sc in sim_context_list
                                               if sc.scenario!=scenario and sc.detector!=detector]
                        if checkit.isChecked():
                            checked = True
                            overwrite = False
                    elif ans_hold == QMessageBox.Yes:
                        shutil.rmtree(directoryName)
                        if checkit.isChecked():
                            checked = True
                            overwrite = True
                else:
                    if overwrite:
                        shutil.rmtree(directoryName)
                    else:
                        sim_context_list[:] = [sc for sc in sim_context_list
                                               if sc.scenario!=scenario and sc.detector!=detector]

            if (detector.includeSecondarySpectrum and detector.secondary_type ==
                    secondary_type['scenario'] and not scenario.scen_bckg_materials):
                ill_defined_scen += 1

        session.close()

        if ill_defined_scen:
            QMessageBox.information(self, self.tr('Not all scenarios were processed'),
                                    self.tr('At least one selected scenario lacks the background '
                                            'definition required to generate a secondary spectrum, '
                                            'and will not be processed.'))
            if ill_defined_scen == len(sim_context_list):
                return True

        # Test one single first to make sure things are working
        try:
            SampleSpectraGenerationGUI(sim_context_list, test=True).work()
        except Exception as e:
            traceback.print_exc()
            logging.exception(self._handled_exception, exc_info=True)
            err_msg = exceptions.text_error_template().render()
            if "secondary_spectrum" in err_msg:
                QMessageBox.critical(self, self.tr('Error!'), self.tr('Sample generation failed for '
                                            '{}<br><br> Please check that the secondary spectrum is '
                                            'defined for this instrument.<br><br>').format(detector.name))
            else:
                QMessageBox.critical(self, self.tr('Error!'), self.tr('Sample generation failed for '
                                            '{}<br> If n42 template is set, please verify it is '
                                            'formatted correctly.<br><br>').format(detector.name) + str(e))
            # shutil.rmtree(directoryName)
            return False

        # now generate all samples
        bar = ProgressBar(self, dispProg)
        bar.title.setText(self.tr('Sample spectra generation in progress'))
        bar.progress.setMaximum(sum(sc.scenario.replication for sc in sim_context_list))
        bar.run(SampleSpectraGenerationGUI(sim_context_list))

        godot = QSignalWait(bar.sig_finished)
        return godot.wait()

    @Slot(bool)
    def on_btnRunReplay_clicked(self, checked):
        replay_gui = ReplayGenerationGUI(self, self.runSelect(), self.settings)
        status = replay_gui.runReplay()
        self.on_action_complete(status, self.tr('Run replay tool'))
        return status

    @Slot(bool)
    def on_btnRunResultsTranslator_clicked(self, checked):
        translator_gui = TranslationGenerationGUI(self, self.runSelect(), self.settings)
        status = translator_gui.runTranslator()
        self.on_action_complete(status, self.tr('Result translation'))

    def on_action_complete(self, exit_status, action_str):
        """
        Displays message dialog when an action is completed
        """
        if exit_status:
            title = self.tr('Success!')
            message = self.tr('{} completed.').format(action_str.capitalize())
        else:
            title = self.tr('{} aborted').format(action_str.capitalize())
            message = self.tr('{} aborted. Not all scenarios were processed.').format(action_str.capitalize())
        QMessageBox.information(self, title, message)
        # update the table colors
        self.updateScenarioColors()

    @Slot(bool)
    def on_actionCorrespondence_Table_triggered(self, checked):
        """
        Launches Correspondence Table Dialog
        """
        CorrespondenceTableDialog().exec_()
        self.settings.setIsAfterCorrespondenceTableCall(True)

    @Slot(bool)
    def on_actionModify_Detector_Influences_triggered(self, checked):
        """
        Launches detector influence table for modification
        """
        if ManageInfluencesDialog(modify_flag=True).exec_():
            self.populateScenarios()

    @Slot(bool)
    def on_actionModify_Material_Weights_triggered(self, checked):
        """
        Launches detector influence table for modification
        """
        ManageWeightsDialog().exec_()

    @Slot(bool)
    def on_btnImportIDResults_clicked(self, checked):
        """
        Imports output of replay tool by copying files to their expected location within RASE file structure
        """
        session = Session()
        scenId = self.getSelectedScenarioIds()[0]
        detName = self.getSelectedDetectorNames()[0]
        repName = self.getSelectedReplayNames()[0]
        detector = session.query(Detector).filter_by(name=detName).first()
        replay = session.query(Replay).filter_by(name=repName).first()
        options = QFileDialog.ShowDirsOnly
        if sys.platform.startswith('win'): options = QFileDialog.DontUseNativeDialog
        dirpath = QFileDialog.getExistingDirectory(self, self.tr('Select folder of results for '
                        'scenario: {} and instrument: {}').format(scenId, detName), get_sample_dir(
                        self.settings.getSampleDirectory(), detector, scenId), options)
        if dirpath:
            resultsDir = get_replay_output_dir(self.settings.getSampleDirectory(), detector, replay, scenId)
            if os.path.normpath(dirpath) != os.path.normpath(resultsDir):
                if os.path.exists(resultsDir):
                    shutil.rmtree(resultsDir)
                shutil.copytree(dirpath, resultsDir)

            self.updateScenarioColors()
            self.updateActionButtons()

    @Slot(bool)
    def on_btnImportSpectra_clicked(self, checked):
        """
        Imports measured (or otherwise generated) sampled spectra by copying files
        to their expected location within RASE file structure
        """
        session = Session()
        scenId = self.getSelectedScenarioIds()[0]
        detName = self.getSelectedDetectorNames()[0]
        repName = self.getSelectedReplayNames()[0]
        detector = session.query(Detector).filter_by(name=detName).first()
        replay = session.query(Replay).filter_by(name=repName).first()
        options = QFileDialog.ShowDirsOnly
        if sys.platform.startswith('win'): options = QFileDialog.DontUseNativeDialog
        dirpath = QFileDialog.getExistingDirectory(self, self.tr('Select folder of sampled spectra '
                             'for scenario: {}, instrument: {} and replay: {}').format(scenId, detName, repName),
                             self.settings.getSampleDirectory(), options)
        if dirpath:
            outDir = get_replay_input_dir(self.settings.getSampleDirectory(), detector, replay, scenId)
            if os.path.normpath(dirpath) != os.path.normpath(outDir):
                if os.path.exists(outDir):
                    shutil.rmtree(outDir)
                os.makedirs(outDir, exist_ok=True)
                for file in glob.glob(os.path.join(dirpath, "*.n42")):
                    shutil.copy(file, outDir)

            self.updateScenarioColors()
            self.updateActionButtons()

    @Slot(bool)
    def on_actionReplay_Software_triggered(self, checked):
        """
        Launches Manage Replays tool
        """
        # ReplayListDialog(self).exec_()
        ManageReplaysDialog().exec_()
        self.populateDetectorReplays()

    @Slot(bool)
    def on_actionModify_Scenario_Groups_triggered(self, checked):
        """
        Launches dialog to delete scenario groups
        """
        GroupSettings(del_groups=True).exec_()
        self.populateAll()

    @Slot(bool)
    def on_actionPreferences_triggered(self, checked):
        """
        Launches Preferences Dialog
        """
        dialog = SettingsDialog(self)
        if dialog.exec():
            if dialog.dataDirectoryChanged:
                Session.remove()
                Session.configure(bind=None)
                initializeDatabase(self.settings.getDatabaseFilepath())
                self.tblScenario.blockSignals(True)
                self.tblDetectorReplay.blockSignals(True)
                self.populateAll()
                self.tblScenario.blockSignals(False)
                self.tblDetectorReplay.blockSignals(False)

    @Slot(bool)
    def on_btnAddScenario_clicked(self, checked):
        """
        Handles adding new Scenario
        """
        s_dialog = ScenarioDialog(self)
        if s_dialog.exec_():
            self.populateScenarios()
        self.populateScenarioGroupCombo()

    @Slot(bool)
    def on_btnAddDetector_clicked(self, checked):
        """
        Handles adding new Detector
        """
        self.d_dialog = DetectorDialog(self)  # attribute of RASE for testing purposes
        if self.d_dialog.exec_():
            self.populateDetectorReplays()
        self.d_dialog = None

    @Slot(QPoint)
    def on_tblScenario_customContextMenuRequested(self, point):
        """
        Handles "Edit" and "Delete" right click selections on the Scenario table
        """
        current_cell = self.tblScenario.itemAt(point)

        # show the context menu only if on an a valid part of the table
        if current_cell:
            scen_ids = self.getSelectedScenarioIds()
            det_names = self.getSelectedDetectorNames()
            rep_names = self.getSelectedReplayNames()

            multiple_cases = len(scen_ids) > 1 or len(det_names) > 1

            # TODO: How to handle plurals?
            deleteAction = QAction(f'Delete Scenario{"s" if multiple_cases else ""}', self)
            editAction = QAction('Edit Scenario', self)
            duplicateAction = QAction(f'New Scenario{"s" if multiple_cases else ""} from this...', self)
            assignAction = QAction(f'Assign Scenario{"s" if multiple_cases else ""} to Group', self)

            menu = QMenu(self.tblScenario)
            menu.addAction(assignAction)
            menu.addAction(deleteAction)
            if not multiple_cases:
                menu.addAction(editAction)
                menu.addAction(duplicateAction)
            menu.addAction(assignAction)

            if multiple_cases:
                first = True
                different_sources = False
                for scenId in scen_ids:
                    if first:
                        first = False
                        dmat = {d.material_name: d.fd_mode for d in Session().query(Scenario).
                                filter_by(id=scenId).first().scen_materials}
                        dback = {d.material_name: d.fd_mode for d in Session().query(Scenario).
                                filter_by(id=scenId).first().scen_bckg_materials}
                    else:
                        if (dmat != {d.material_name: d.fd_mode for d in
                                     Session().query(Scenario).filter_by(id=scenId).first().scen_materials} or
                                dback != {d.material_name: d.fd_mode for d in
                                          Session().query(Scenario).filter_by(id=scenId).first().scen_bckg_materials}):
                            different_sources = True
                            break
                if not different_sources:
                    menu.addAction(duplicateAction)

            # The action to open the sample folders shows up only
            # if the sample folders exists and a detector is selected
            sampleDirs = []
            sampleDirs_only_replays = []
            for scen in scen_ids:
                for det_name, rep_name in zip(det_names, rep_names):
                    detector = Session().query(Detector).filter_by(name=det_name).first()
                    replay = Session().query(Replay).filter_by(name=rep_name).first()
                    dir = get_sample_dir(self.settings.getSampleDirectory(), detector, scen)
                    if files_endswith_exists(dir, ('.n42',)):
                        sampleDirs.append(dir)
                    elif os.path.exists(get_replay_output_dir(self.settings.getSampleDirectory(), detector, replay, scen)):
                        sampleDirs_only_replays.append(dir)
            if (len(sampleDirs) + len(sampleDirs_only_replays)) > 1:
                action_label = 'Go To Sample Folders'
                viewSampleSpectraAction = False
                if (len(sampleDirs) + len(sampleDirs_only_replays)) < 6:
                    viewSummedSpectraAction = QAction(self.tr('Compare Summed Sample Spectra'), self)
                else:
                    viewSummedSpectraAction = QAction(self.tr('Compare Summed Sample Spectra (max 5)'), self)
                    viewSummedSpectraAction.setEnabled(False)
            else:
                action_label = 'Go To Sample Folder'
                viewSampleSpectraAction = QAction(self.tr('View Sample Spectra'), self)
                viewSummedSpectraAction = QAction(self.tr('View Summed Sample Spectra'), self)

            goToFolderAction = QAction(action_label, self)
            if sampleDirs and viewSampleSpectraAction:
                menu.addAction(viewSampleSpectraAction)
            if sampleDirs and viewSummedSpectraAction:
                menu.addAction(viewSummedSpectraAction)
            if sampleDirs or sampleDirs_only_replays:
                menu.addAction(goToFolderAction)

            # execute actions
            action = menu.exec(self.tblScenario.mapToGlobal(point))
            if action == deleteAction:
                delete_scenario(scen_ids, self.settings.getSampleDirectory())
                self.populateAll()
            elif action == goToFolderAction:
                for dir in sampleDirs + sampleDirs_only_replays:
                    fileBrowser = 'explorer' if sys.platform.startswith('win') else 'open'
                    subprocess.Popen([fileBrowser, dir])
            elif action == editAction:
                self.edit_scenario(scen_ids[0])  # same as 'scen'; what is better coding practice?
            elif action == duplicateAction:
                self.duplicate_scen(scen_ids[0])
            elif action == assignAction:
                self.assign_to_group(scen_ids)
            elif action == viewSampleSpectraAction:
                scenario = Session().query(Scenario).filter_by(id=scen_ids[0]).first()
                detector = Session().query(Detector).filter_by(name=det_names[0]).first()
                SampleSpectraViewerDialog(self, scenario, detector, 0).exec_()
            elif action == viewSummedSpectraAction:
                MultiSpecViewerDialog(self, sampleDirs).exec()


    @Slot(bool)
    def on_btnSampleDir_clicked(self, checked):
        """
        Opens the generated samples directory in File Explorer
        """
        fileBrowser = 'explorer' if sys.platform.startswith('win') else 'open'
        subprocess.Popen([fileBrowser, self.settings.getSampleDirectory()])

    @Slot(bool)
    def on_btnViewResults_clicked(self, checked):
        """
        Opens Results table
        """
        # need a correspondence table in order to display results!
        session = Session()
        default_corr_table = session.query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
        if not default_corr_table:
            QMessageBox.critical(self, self.tr('Error!'), self.tr('Please set a default correspondence table'))
            return
        ViewResultsDialog(self, self.runSelect()).open()


    @Slot(int)
    def on_cmbScenarioGroups_currentIndexChanged(self, text):
        self.populateScenarios()

    @Slot(str)
    def on_txtScenarioSearch_textEdited(self, text):
        self.populateScenarios()

    @Slot(str)
    def on_txtDetectorSearch_textEdited(self, text):
        self.populateDetectorReplays()

    @Slot(bool)
    def on_actionHelp_triggered(self, checked):
        """
        Shows help dialog
        """
        if not self.help_dialog:
            self.help_dialog = HelpDialog()
        if self.help_dialog.isHidden():
            self.help_dialog.show()
        self.help_dialog.activateWindow()

    @Slot(bool)
    def on_actionAbout_triggered(self, checked):
        """
        show About Dialog
        """
        AboutRASEDialog(self).exec_()

    @Slot(bool)
    def on_actionInput_Random_Seed_triggered(self, checked):
        """
        Launches Random Seed Dialog
        """
        dialog = RandomSeedDialog(self)
        dialog.exec_()

    @Slot(bool)
    def on_actionBase_Spectra_Creation_Tool_triggered(self, checked):
        dialog = CreateBaseSpectraDialog(self)
        dialog.exec_()

    @Slot(bool)
    def on_actionBase_Spectra_Creation_Wizard_triggered(self, checked):
        dialog = CreateBaseSpectraWizard(self)
        dialog.exec_()

    @Slot(bool)
    def on_actionShielded_Base_Spectra_Creation_triggered(self, checked):
        dialog = CreateShieldedSpectraDialog(self)
        dialog.exec_()

    @Slot(bool)
    def on_actionAutomated_Scurve_triggered(self, checked):
        """
        Launches S-curve
        """
        # must check if there is a correspondence table set, otherwise it will bug out
        corrTable = Session().query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
        if not corrTable:
            QMessageBox.critical(self, self.tr('Set Correspondence Table'),
                                 self.tr('Must specify a Correspondence Table'))
            return

        dialog = AutomatedSCurve(self)
        selection = dialog.exec()
        if selection == 1:
            generate_curve(dialog.input_d, dialog.input_advanced, self)
            self.populateScenarios()
            self.populateScenarioGroupCombo()


class SampleSpectraGenerationGUI(SampleSpectraGeneration, QObject):
    """
    Shell class to enable GUI operation of spectra generation
    """
    sig_step = Signal(int)
    sig_done = Signal(bool)

    def __init__(self, sim_context_list: list[SimContext], test=False, samplepath=None):
        super().__init__(sim_context_list, test, samplepath)
        super(SampleSpectraGeneration, self).__init__()

    def _gui_sigdone_emit(self):
        if self._abort:
            self.sig_done.emit(False)
        else:
            self.sig_done.emit(True)

    def _gui_process_events(self):
        QApplication.processEvents()  # this could cause change to self._abort

    def _gui_sigstep_emit(self, count):
        self.sig_step.emit(count)


class ReplayGenerationGUI(ReplayGeneration, QObject):
    def __init__(self, parent, sim_context_list: list[SimContext], settings=None):
        self.parent = parent
        super().__init__(sim_context_list, settings)
        super(ReplayGeneration, self).__init__()

    def _gui_progress_bar(self):
        progress = QProgressDialog(self.parent.tr('Replay in progress...'), None, 0, self.n + 1, self.parent)
        progress.setMinimumDuration(0)
        progress.setMaximum(self.n + 1)
        progress.setWindowModality(Qt.WindowModal)
        progress.forceShow()
        return progress

    def _gui_set_value(self, value):
        if self.progress is not None:
            self.progress.setValue(value)

    def _gui_set_label(self, label):
        if self.progress is not None:
            self.progress.setLabelText(label)

    def _gui_QCritical(self, err_name='', err_message=''):
        try:
            QMessageBox.critical(self.parent, err_name, err_message)
        except:
            traceback.print_exc()
            logging.exception(self.parent._handled_exception, exc_info=True)

    def _gui_QInformation(self, info_name='', info_message=''):
        try:
            QMessageBox.information(self.parent, info_name, info_message)
        except:
            traceback.print_exc()
            logging.exception(self.parent._handled_exception, exc_info=True)

    def _gui_update_colors(self):
        try:
            self.parent.updateScenarioColors()
        except:
            traceback.print_exc()
            logging.exception(self.parent._handled_exception, exc_info=True)


class TranslationGenerationGUI(TranslationGeneration, QObject):
    def __init__(self, parent=None, sim_context_list: list[SimContext]=None, settings=None):
        self.parent = parent
        super().__init__(sim_context_list, settings)
        super(TranslationGeneration, self).__init__()

    def _gui_progress_bar(self):
        progress = QProgressDialog(self.parent.tr('Translation in progress...'), self.parent.tr('Abort'),
                                   0, self.n + 1, self.parent)
        progress.setMinimumDuration(0)
        progress.setMaximum(self.n + 1)
        progress.setWindowModality(Qt.WindowModal)
        return progress

    def _gui_set_value(self, value):
        if self.progress is not None:
            self.progress.setValue(value)

    def _gui_set_label(self, label):
        if self.progress is not None:
            self.progress.setLabelText(label)

    def _gui_QCritical(self, err_name='', err_message=''):
        try:
            QMessageBox.critical(self.parent, err_name, err_message)
        except:
            traceback.print_exc()
            logging.exception(self.parent._handled_exception, exc_info=True)


class HtmlDelegate(QStyledItemDelegate):
    '''render html text passed to the table widget item'''

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        style = option.widget.style() if option.widget else QApplication.style()

        palette = QApplication.palette()
        color = palette.highlight().color() \
            if option.state & QStyle.State_Selected \
            else palette.base()
        ctx = QAbstractTextDocumentLayout.PaintContext()
        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, option)

        painter.save()
        painter.fillRect(option.rect, color)
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))

        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        fm = option.fontMetrics
        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setHtml(index.model().data(index))
        return QSize(int(document.idealWidth()) + 20, int(fm.height()))


class AboutRASEDialog(ui_about_dialog.Ui_aboutDialog, QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setupUi(self)
