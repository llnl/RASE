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
This module allows user to input seed for Random Number Generation to ensure reproducible
validation results
"""

from PySide6.QtCore import Slot, QRegularExpression, QSize, Qt, QCoreApplication
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTableView, QSizePolicy, QVBoxLayout
from PySide6.QtGui import QRegularExpressionValidator

from src.rase_settings import RaseSettings
from src.ui_generated import ui_auto_scurve
from src.table_def import Session, Detector
from src.scenario_dialog import BgndTableModel, UNITS, MATERIAL, INTENSITY, MaterialDoseDelegate

# translation_tag = 'auto_sd'


class AutomatedSCurve(ui_auto_scurve.Ui_AutoSCurveDialog, QDialog):
    def __init__(self, parent, model=None):
        QDialog.__init__(self, parent)
        self.Rase = parent
        self.settings = RaseSettings()
        self.setupUi(self)
        self.setWindowTitle(self.tr('Automated S-Curve Generation'))
        self.session = Session()
        self.model = SCurveModel(model)
        self.bgnd_model = BgndTableModel()

        # setting default states
        self.detector = None
        self.replay = None
        self.setInstrumentItems()
        self.setReplayItems()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        # Validators
        self.line_rep.setValidator(QRegularExpressionValidator(QRegularExpression(r'[0-9]{0,9}')))
        self.line_initrep.setValidator(QRegularExpressionValidator(QRegularExpression(r'[0-9]{0,9}')))
        self.line_edge.setValidator(QRegularExpressionValidator(QRegularExpression(r'[0-9]{0,9}')))
        self.line_ends.setValidator(QRegularExpressionValidator(QRegularExpression(r'[0-9]{0,9}')))
        self.line_dwell.setValidator(QRegularExpressionValidator(QRegularExpression(r'((\d*\.\d*)|(\d*))')))
        self.line_minx.setValidator(QRegularExpressionValidator(QRegularExpression(r'((\d*\.\d*)|(\d*))')))
        self.line_maxx.setValidator(QRegularExpressionValidator(QRegularExpression(r'((\d*\.\d*)|(\d*))')))
        self.line_addpoints.setValidator(QRegularExpressionValidator(QRegularExpression(
                                r'((((\d+\.\d*)|(\d*\.\d+))|(\d+))((((,\d*\.\d+)|(,\d+\.\d*))|(,\d+))*)(,|,\.)?)')))
        self.line_lowerbound.setValidator(QRegularExpressionValidator(QRegularExpression(r'((\d*\.\d*)|(\d*))')))
        self.line_upperbound.setValidator(QRegularExpressionValidator(QRegularExpression(r'((\d*\.\d*)|(\d*))')))

        # connections
        self.combo_inst.currentTextChanged.connect(self.updateMaterials)
        self.combo_inst.currentTextChanged.connect(self.updateSelection)
        self.combo_inst.currentTextChanged.connect(self.setReplayItems)
        self.combo_replay.currentTextChanged.connect(self.updateSelection)
        self.combo_mat.currentTextChanged[str].connect(lambda mat: self.updateUnits(mat, self.combo_matdose))
        self.btn_bgnd.clicked.connect(self.defineBackground)

        # Confirm enables
        self.combo_matdose.currentTextChanged.connect(self.enableOk)

        # Set values of various things based on user inputs
        self.line_rep.editingFinished.connect(lambda: self.setminval(self.line_rep, '2'))
        self.line_initrep.editingFinished.connect(lambda: self.setminval(self.line_initrep, '1'))
        self.line_edge.editingFinished.connect(lambda: self.setminval(self.line_edge, '1'))
        self.line_ends.editingFinished.connect(lambda: self.setminval(self.line_ends, '1'))
        self.line_dwell.editingFinished.connect(lambda: self.setminval(self.line_dwell, '1', '0.00000000001'))
        self.line_minx.editingFinished.connect(lambda: self.setminval(self.line_minx, str(self.model.default_values['min_guess']), '0.00000000001'))
        self.line_maxx.editingFinished.connect(lambda: self.setminval(self.line_maxx, str(self.model.default_values['max_guess']), '0.00000000001'))
        self.line_lowerbound.editingFinished.connect(lambda: self.setminval(self.line_lowerbound, '0'))
        self.line_lowerbound.editingFinished.connect(lambda: self.setmaxval(self.line_lowerbound, '.99'))
        self.line_upperbound.editingFinished.connect(lambda: self.setmaxval(self.line_upperbound, '1'))
        self.line_minx.editingFinished.connect(self.checkMaxX)
        self.line_maxx.editingFinished.connect(self.checkMaxX)
        self.line_lowerbound.editingFinished.connect(self.checkMaxY)
        self.line_upperbound.editingFinished.connect(self.checkMaxY)
        self.line_addpoints.editingFinished.connect(self.removeZeroPoint)
        self.check_minx.stateChanged.connect(self.setDefaultMin)
        self.check_maxx.stateChanged.connect(self.setDefaultMax)
        self.check_addpoints.stateChanged.connect(self.setAddPoints)
        self.check_name.stateChanged.connect(self.setDefaultName)

        self.set_default_values()

    def set_default_values(self):
        # first the combo boxes
        if self.model.instrument != '' and self.model.instrument in [self.combo_inst.itemText(i)
                                                         for i in range(self.combo_inst.count())]:
            self.combo_inst.setCurrentText(self.model.instrument)
        if self.model.source != '' and self.model.source in [self.combo_mat.itemText(i) for i
                                                                 in range(self.combo_mat.count())]:
            self.combo_mat.setCurrentText(self.model.source)
        if self.model.source_fd != '' and self.model.source_fd in [self.combo_matdose.itemText(
                i).split()[0] for i in range(1, self.combo_matdose.count())]:
            if self.model.source_fd == 'FLUX':
                self.combo_matdose.setCurrentText(self.tr('FLUX (\u03B3/(cm\u00B2s))'))
            else:
                self.combo_matdose.setCurrentText(self.tr('DOSE (\u00B5Sv/h)'))
        if self.model.results_type in [self.combo_resulttype.itemText(i) for i in range(
                self.combo_resulttype.count())]:
            self.combo_resulttype.setCurrentText(self.model.results_type)
        # then the background
        if self.model.background:
            try:
                self.bgnd_model.setDataFromTable(self.model.background)
            except:
                self.bgnd_model.reset_data()
        # then the check boxes
        self.check_invert.setChecked(self.model.invert_curve)
        self.check_cleanup.setChecked(self.model.cleanup)
        self.check_name.setChecked(self.model.custom_name != self.model.default_values['custom_name'])
        self.check_minx.setChecked(self.model.min_guess != self.model.default_values['min_guess'])
        self.check_maxx.setChecked(self.model.max_guess != self.model.default_values['max_guess'])
        self.check_addpoints.setChecked(self.model.add_points != self.model.default_values['add_points'])
        # finally, the text boxes
        self.line_dwell.setText(str(self.model.dwell_time))
        self.line_rep.setText(str(self.model.input_reps))
        self.line_edge.setText(str(self.model.rise_points))
        self.line_ends.setText(str(self.model.end_points))
        self.line_minx.setText(str(self.model.min_guess))
        self.line_maxx.setText(str(self.model.max_guess))
        self.line_initrep.setText(str(self.model.repetitions))
        self.line_addpoints.setText(str(self.model.add_points))
        self.line_name.setText(str(self.model.custom_name))
        self.line_lowerbound.setText(str(self.model.lower_bound))
        self.line_upperbound.setText(str(self.model.upper_bound))

    def setInstrumentItems(self):
        for detector in self.session.query(Detector):
            # check if there is at least one runnable replay associated with this detector
            runnable_replays = [r for r in detector.replays if r.is_runnable]
            if runnable_replays:
                self.combo_inst.addItem(detector.name, detector)

    def setReplayItems(self):
        self.combo_replay.clear()
        if det_name:=self.combo_inst.currentText():
            detector = self.session.query(Detector).filter_by(name=det_name).first()
            for replay in detector.replays:
                if replay.is_runnable():
                   self.combo_replay.addItem(replay.name, replay)

    @Slot(str)
    def updateMaterials(self, detName):
        """
        Updates the possible material selection based on the selected instrument.
        Also identify the name of the replay associated with the chosen detector
        and set it for S-curve processing
        """
        self.combo_mat.clear()
        self.combo_mat.addItem('')

        if not detName.strip():
            self.combo_mat.setCurrentIndex(0)
            self.combo_mat.setEnabled(False)
            self.btn_bgnd.setEnabled(False)
        else:
            self.combo_mat.setEnabled(True)
            self.btn_bgnd.setEnabled(True)
            det = self.combo_inst.currentData()
            for baseSpectrum in sorted(det.base_spectra, key=lambda x: x.material.name):
                self.combo_mat.addItem(baseSpectrum.material.name)

    @Slot(str)
    def updateSelection(self, text):
        self.detector = self.combo_inst.currentData()
        self.replay = self.combo_replay.currentData()
        self.bgnd_model.detector_selection = self.detector.name

    def updateUnits(self, matName, combobox):
        """
        General function call for updating the flux/dose setting in the
        combobox after material has been selected
        """
        combobox.clear()
        combobox.addItem('')
        if not matName.strip():
            combobox.setCurrentIndex(0)
            combobox.setEnabled(False)
        else:
            combobox.setEnabled(True)
            for baseSpectrum in self.detector.base_spectra:
                if baseSpectrum.material_name == matName:
                    if baseSpectrum.rase_sensitivity:
                        combobox.addItem(self.tr('DOSE (\u00B5Sv/h)'))
                        combobox.setCurrentIndex(1)
                    if baseSpectrum.flux_sensitivity:
                        combobox.addItem(self.tr('FLUX (\u03B3/(cm\u00B2s))'))
                        if combobox.count() == 2:       # dose is default
                            combobox.setCurrentIndex(1)


    @Slot(str)
    def enableOk(self, intensity):
        """Only enable the okay button if all the relevant points are selected"""
        if self.combo_matdose.currentText() and self.line_dwell.text() and \
                self.line_maxx.text() and self.line_minx.text():
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    def changeMinMax(self):
        """Change the min and max guess based on the background intensity"""

        if not self.check_minx.isChecked():
            minv = str(1E-7)
            minv = self.checkSciNote(minv)
            self.line_minx.setText(minv)
            self.checkMaxX()
            self.setAddPoints()
        if not self.check_maxx.isChecked():
            maxv = str(1E-2)
            maxv = self.checkSciNote(maxv)
            self.line_maxx.setText(maxv)
            self.checkMaxX()

    def checkSciNote(self, val):
        """If there is scientific notation, remove it so as to not break regex"""
        if 'E' in val.upper():
            sci = val.upper().split('E')
            if int(sci[1]) < 0:
                val = '0.' + ''.zfill(abs(int(sci[1])) - 1) + sci[0].replace('.', '')
            else:
                val = str(float(sci[0]) * 10 ** int(sci[1]))
        return val

    def setminval(self, line, setval='0.00000001', minval=None):
        if not minval:
            minval = setval
        try:
            if float(line.text()) <= float(minval):
                line.setText(setval)
        except:  # if the user enters a decimal point or something nonsensical
            line.setText(setval)

    def setmaxval(self, line, setval='1', maxval=None):
        if not maxval:
            maxval = setval
        try:
            if float(line.text()) >= float(maxval):
                line.setText(setval)
        except:  # if the user enters a decimal point or something nonsensical
            line.setText(setval)

    def checkMaxX(self):
        """Make sure the maximum x value is larger than the minimum x value"""
        if self.line_maxx.text() and self.line_minx.text():
            if float(self.line_maxx.text()) <= float(self.line_minx.text()):
                self.line_maxx.setText(str(float(self.line_minx.text()) * 1E5))

    def checkMaxY(self):
        """Make sure that the bounds don't overlap each other"""
        if self.line_upperbound.text() and self.line_lowerbound.text():
            if float(self.line_upperbound.text()) <= float(self.line_lowerbound.text()):
                self.line_upperbound.setText(str(max([0.9, float(self.line_lowerbound.text())*1.01])))

    def setDefaultMin(self):
        """Set the default minimum x value if it has been unchecked"""
        if not self.check_minx.isChecked():
            self.line_minx.setText(str(self.model.default_values['min_guess']))
            self.setAddPoints()
            self.checkMaxX()

    def setDefaultMax(self):
        """Set the default max x value if it has been unchecked"""
        if not self.check_maxx.isChecked():
            self.line_maxx.setText(str(self.model.default_values['max_guess']))
            self.checkMaxX()

    def setAddPoints(self):
        """Set default user-added points and clears them if the box is unchecked"""
        if self.check_addpoints.isChecked():
            if not self.line_addpoints.text():
                self.line_addpoints.setText(str(self.line_minx.text()))
        else:
            self.line_addpoints.setText('')

    def setDefaultName(self):
        """Set name back to [Default] if the checkbox is unchecked"""
        if not self.check_name.isChecked():
            self.line_name.setText(str(self.model.default_values['custom_name'])) # should be str anyways, but good to doublecheck

    def removeZeroPoint(self):
        """Disallow the user to add a point with 0 dose/flux"""
        if self.line_addpoints.text():
            self.line_addpoints.setText(self.endRecurse(self.line_addpoints.text()))
            addpoints = [float(i) for i in self.line_addpoints.text().split(',')]
            if 0 in addpoints:
                addpoints = [i for i in addpoints if i != 0]
            addpoints = list(dict.fromkeys(addpoints))
            addpoints.sort()
            addpoints = [self.checkSciNote(str(i)) for i in addpoints]
            addpoints = str(addpoints)[1:-1].replace('\'', '').replace(' ', '')
            self.line_addpoints.setText(addpoints)

    def endRecurse(self, line):
        """Remove commas/periods at the end of the uesr-adde points list, recursively"""
        if (line[-1] == ',') or (line[-1] == '.'):
            return self.endRecurse(line[:-1])
        else:
            return line

    def defineBackground(self):
        """
        Allow the user to setup the backgrounds
        @return:
        """
        backup_data = self.bgnd_model.model_data.copy(deep=True)
        if self.create_bgnd_gui():
            for row in range(self.bgnd_model.rowCount()):
                if '' in [self.bgnd_model.data(self.bgnd_model.index(row, col)) for col in
                                                [UNITS, MATERIAL, INTENSITY]]:
                    for col in [UNITS, INTENSITY, MATERIAL]:
                        self.bgnd_model.setData(self.bgnd_model.index(row, col), '')
        else:
            self.bgnd_model.setDataFromTable(backup_data.to_numpy())

    def create_bgnd_gui(self):
        """
        Create and execute the static background GUI
        @return:
        """
        dialog = QDialog()
        # background table
        tblBackground = QTableView(dialog)
        tblBackground.setObjectName(u'tblBackground')
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHeightForWidth(tblBackground.sizePolicy().hasHeightForWidth())
        tblBackground.setSizePolicy(sizePolicy1)
        tblBackground.setMinimumSize(QSize(440, 0))
        tblBackground.setShowGrid(True)
        tblBackground.setGridStyle(Qt.SolidLine)
        tblBackground.horizontalHeader().setMinimumSectionSize(140)
        tblBackground.horizontalHeader().setStretchLastSection(True)
        tblBackground.verticalHeader().setVisible(False)
        tblBackground.verticalHeader().setCascadingSectionResizes(True)
        tblBackground.setModel(self.bgnd_model)
        tblBackground.setItemDelegate(MaterialDoseDelegate(self.bgnd_model, unitsCol=UNITS,
                                                    materialCol=MATERIAL,
                                                    intensityCol=INTENSITY,
                                                    selected_detname=self.bgnd_model.detector_selection,
                                                    auto_s=True,
                                                    tables=[self.bgnd_model]))
        # button box
        buttonBox = QDialogButtonBox(dialog)
        buttonBox.setObjectName(u'buttonBox')
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        # layout
        layout = QVBoxLayout(dialog)
        layout.addWidget(tblBackground)
        layout.addWidget(buttonBox)
        dialog.resize(430, 250)
        dialog.setWindowTitle(self.tr('Set static background for {}.').format(self.bgnd_model.detector_selection))

        return dialog.exec_()

    @Slot()
    def accept(self):
        if self.line_addpoints.text():
            addpoints = [float(i) for i in self.line_addpoints.text().split(',')]
        else:
            addpoints = []
        self.model.instrument = self.detector.name
        self.model.replay = self.replay.name
        self.model.source = self.combo_mat.currentText()
        self.model.source_fd = self.combo_matdose.currentText().split()[0]
        self.model.background = [list(row) for row in self.bgnd_model.model_data.to_numpy() if not '' in row[:3]]
        self.model.dwell_time = float(self.line_dwell.text())
        self.model.results_type = self.combo_resulttype.currentText()
        self.model.input_reps = int(self.line_rep.text())
        self.model.invert_curve = self.check_invert.isChecked()

        self.model.rise_points = int(self.line_edge.text())
        self.model.end_points = int(self.line_ends.text())
        self.model.min_guess = float(self.line_minx.text())
        self.model.max_guess = float(self.line_maxx.text())
        self.model.repetitions = int(self.line_initrep.text())
        self.model.add_points = addpoints
        self.model.cleanup = self.check_cleanup.isChecked()
        self.model.custom_name = self.line_name.text()
        self.model.num_points = self.model.num_points   # hardcode to default for now
        self.model.lower_bound = float(self.line_lowerbound.text())
        self.model.upper_bound = float(self.line_upperbound.text())

        self.input_d, self.input_advanced = self.model.accept()

        return QDialog.accept(self)


class SCurveModel:
    def __init__(self, model=None):
        self.default_values = {'instrument': None,
                               'replay': None,
                               'source': None,
                               'source_fd': None,
                               'background': [],
                               'dwell_time': 30,
                               'input_reps': 100,
                               'results_type': 'PID',
                               'invert_curve': False,
                               'rise_points': 5,
                               'end_points': 3,
                               'min_guess': 0.00000001,
                               'max_guess': 0.001,
                               'repetitions': 10,
                               'add_points': '',
                               'cleanup': False,
                               'custom_name': QCoreApplication.translate('auto_sd', '[Default]'),
                               'num_points': 6,
                               'lower_bound': 0.1,
                               'upper_bound': 0.9
                               }
        for key in self.default_values:
            setattr(self, key, self.default_values[key])
        # override defaults if passing a model (possibly enabling import in the future?)
        if model is not None:
            for key in self.default_values:
                setattr(self, key, model.__getattribute__(key))

    def accept(self):
        input_d = {'instrument': self.instrument,
                    'replay': self.replay,
                    'source': self.source,
                    'source_fd': self.source_fd,
                    'background': self.background,
                    'dwell_time': self.dwell_time,
                    'results_type': self.results_type,
                    'input_reps': self.input_reps,
                    'invert_curve': self.invert_curve
                    }
        input_a = {'rise_points': self.rise_points,
                   'min_guess': self.min_guess,
                   'max_guess': self.max_guess,
                   'repetitions': self.repetitions,
                   'add_points': self.add_points,
                   'end_points': self.end_points,
                   'cleanup': self.cleanup,
                   'custom_name': self.custom_name,
                   'num_points': self.num_points,  # hardcode for now
                   'lower_bound': self.lower_bound,
                   'upper_bound': self.upper_bound
                   }

        return input_d, input_a