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
This module specifies the base spectra, influences, and other detector info
"""
import logging
from PySide6.QtCore import Qt, Slot, QRegularExpression, QAbstractItemModel, QAbstractListModel, QModelIndex, \
    QAbstractTableModel
from PySide6.QtGui import QRegularExpressionValidator, QDoubleValidator
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QItemDelegate, QLineEdit, QComboBox, \
    QInputDialog, QDataWidgetMapper, QAbstractItemView, QHeaderView
from sqlalchemy import inspect

from src.base_spectra_dialog import BaseSpectraDialog
from src.create_shielded_spectra_dialog import CreateShieldedSpectraDialog
from src.manage_replays_dialog import ManageReplaysDialog
from src.manage_influences_dialog import ManageInfluencesDialog
from src.plotting import BaseSpectraViewerDialog
from src.qt_utils import BaseSpectraListModel
from src.rase_functions import secondary_type  # , secondary_index, importDistortionFile
from src.rase_settings import RaseSettings
from src.replay_dialog import ReplayDialog
from src.table_def import Session, Replay, Detector, Influence, DetectorSchema, \
    SecondarySpectrum, BackgroundSpectrum, Spectrum
from src.ui_generated import ui_add_detector_dialog

import yaml

# translation_tag = 'det_d'

class DetectorDialog(ui_add_detector_dialog.Ui_Dialog, QDialog):
    def __init__(self, parent, detectorName=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setupUi(self)
        self.modelBSL = BaseSpectraListModel()
        self.lstBaseSpectra.setModel(self.modelBSL)
        self.modelINL = InfluenceListModel()
        self.listInfluences.setModel(self.modelINL)
        self.model = DetectorModel(detectorName)
        self.model_lineedits = [self.txtDetector, self.txtManufacturer,
                   self.txtClassCode, self.txtHardwareVersion, self.txtInstrumentId,
                   self.txtChannelCount, self.txtEcal0, self.txtEcal1, self.txtEcal2, self.txtEcal3]
        self.settings = RaseSettings()
        self.newBaseSpectra = []
        self.newBackgroundSpectrum = None
        self.internal_secondary = 'None'
        self.settingProgramatically = False
        self.detectorInfluences = []
        self.editDetector = False

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.model)
        self.set_modelmap()
        self.mapper.toFirst()

        # background combo_box
        self.secondarymap_indexes = {0: 'base_spec', 1: 'scenario', 2: 'file'}

        self.session = Session()

        self.noSecondaryRadio.toggled.connect(lambda: setattr(self.model, 'no_secondary',
                                                              self.noSecondaryRadio.isChecked()))
        self.noSecondaryRadio.setChecked(True)
        self.checkAddIntrinsic.setEnabled(False)
        self.checkAddIntrinsic.toggled.connect(self.addIntrinsicToggle)
        self.checkAddIntrinsic.toggled.connect(lambda: self.model.setData(self.model.index(
                                                    0, self.model.column_dict['sample_intrinsic']),
                                                    self.checkAddIntrinsic.isChecked()))
        self.secondaryIsBackgroundRadio.toggled.connect(self.setSecondarySpecEnable)
        self.combo_typesecondary.setCurrentIndex(1)
        self.combo_typesecondary.currentIndexChanged.connect(self.enableComboBase)
        self.combo_typesecondary.currentIndexChanged.connect(lambda: setattr(self.model, 'detector_type_secondary',
                                self.secondarymap_indexes[self.combo_typesecondary.currentIndex()]))
        self.includeSecondarySpectrumCheckBox.setEnabled(False)

        self.btnAddInfluences.clicked.connect(lambda: self.influenceManagement(False))
        self.btnModifyInfluences.clicked.connect(lambda: self.influenceManagement(True))
        self.btnDeleteInfluences.clicked.connect(self.deleteInfluencesFromDetector)
        self.manageReplays.clicked.connect(self.replayManagement)
        self.lstBaseSpectra.doubleClicked.connect(self.showSpectrum)
        self.label_intrinsicWarning.setVisible(False)

        # TODO: put these in setters that take care of their typing! 10/21
        self.txtDetector.textChanged.connect(self.enable_export)
        self.txtChannelCount.textChanged.connect(lambda: self.model.set_chan_count(self.txtChannelCount.text()))
        self.combo_basesecondary.currentIndexChanged.connect(lambda: setattr(self.model, 'base_secondary',
                                                         self.combo_basesecondary.currentText()))
        self.combo_selectIntrinsic.currentIndexChanged.connect(lambda:
                   self.model.set_intrinsic_classcode(self.combo_selectIntrinsic.currentText()))
        self.cb_resample.toggled.connect(lambda: self.model.set_bgnd_spec_resample(
                                                                    self.cb_resample.isChecked()))
        self.spinBox_secondarydwell.textChanged.connect(lambda: self.model.set_bgnd_spec_dwell(
                                                    float(self.spinBox_secondarydwell.text()[:-1])))
        self.modelBSL.layoutChanged.connect(lambda: self.btnCreateShieldSpec.setEnabled(self.modelBSL.rowCount() > 0))

        self.model.reinitialize_detector(detectorName)
        self.model.get_db_detnames(detectorName)

        self.tblViewReplay.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tblViewReplay.setSelectionMode(QAbstractItemView.NoSelection)
        self.tblViewReplay.setSortingEnabled(False)  # If enabling sorting, a QSortFilterProxyModel is needed
        self.replay_tbl_model = ReplayTableModel(replays=self.session.query(Replay).all(),
                                                 detector=self.detector)
        self.tblViewReplay.setModel(self.replay_tbl_model)

        self.populate_gui_from_detector(detectorName)
        self.enable_export()

    def set_modelmap(self):
        col_names = [col.name for col in self.model.detector.__table__.columns][1:]
        for w, c in zip(self.model_lineedits, col_names):
            self.mapper.addMapping(w, self.model.column_dict[c])

    def handleEditingFinished(self):
        # must grab them at the beginning to make sure that the scenario update doesn't replace
        # the values in the process
        linetexts = [lineedit.text() if type(lineedit) ==
                     QLineEdit else lineedit.toPlainText() for lineedit in self.model_lineedits]
        for linetext, line_edit in zip(linetexts, self.model_lineedits[1:]):
            column = self.model_lineedits.index(line_edit)
            self.model.setData(self.model.index(0, column), linetext, Qt.EditRole)

    def populate_gui_from_detector(self, detectorName):
        # case that this is an edit of an existing detector
        if detectorName:
            # populate materials
            self.modelBSL.add_spectra(self.detector.base_spectra)
            self.set_neutrons_display()

            if self.detector.base_spectra:
                self.includeSecondarySpectrumCheckBox.setEnabled(True)
                self.changeIntrinsicText(self.detector.base_spectra)
        if self.detector.secondary_spectra:
            self.checkAddIntrinsic.setEnabled(True)
            if self.detector.sample_intrinsic:
                self.checkAddIntrinsic.setChecked(True)  # combo_selectIntrinsic populated here
                self.combo_selectIntrinsic.setCurrentIndex(
                    self.combo_selectIntrinsic.findText(self.detector.intrinsic_classcode))
        elif self.editDetector:
            self.combo_typesecondary.removeItem(secondary_type['file'])
        if self.detector.includeSecondarySpectrum:
            if self.detector.secondary_type is None:  # this can only happen if there is an intrinsic
                self.noSecondaryRadio.setChecked(True)
            else:
                self.secondaryIsBackgroundRadio.setChecked(True)
                self.combo_typesecondary.setEnabled(True)
                for key, val in secondary_type.items():
                    if val == self.detector.secondary_type:
                        self.combo_typesecondary.setCurrentIndex(secondary_type[key])
                        break
        self.modelINL.add_influences(self.detector.influences)

    @property
    def detector(self):
        return self.model.detector
    @detector.setter
    def detector(self, value):
        self.model.detector = value

    @property
    def replay(self):
        return self.model.replay
    @replay.setter
    def replay(self, value):
        self.model.replay = value

    @property
    def editDetector(self):
        return self.model.editDetector
    @editDetector.setter
    def editDetector(self, value):
        self.model.editDetector = value

    def replayManagement(self):
        """
        Opens Manage Replays Dialog
        """
        manageRepDialog = ManageReplaysDialog()
        manageRepDialog.exec_()
        self.refresh_replays()

    def influenceManagement(self, modify_flag=False):
        """
        Opens the Influences Dialog
        """
        manageInflDialog = ManageInfluencesDialog(self, modify_flag)
        if manageInflDialog.exec_():
            self.model.append_influences(self.modelINL.influences)

    def deleteInfluencesFromDetector(self):
        """
        Removes selected influences from influence list
        """
        self.modelINL.remove_influence(self.listInfluences.currentIndex())
        self.model.append_influences(self.modelINL.influences)

    def showSpectrum(self):
        """
        Plot loaded base spectra
        """
        spectra = self.newBaseSpectra
        if not self.newBaseSpectra:
            spectra = self.detector.base_spectra
        d = BaseSpectraViewerDialog(self, spectra, self.detector, self.modelBSL.data(
                                            self.lstBaseSpectra.currentIndex(), Qt.DisplayRole))
        d.exec_()

    def addIntrinsicToggle(self, checked=False):
        """All cosmetic"""
        if checked:
            self.noSecondaryRadio.setText(self.tr('No secondary spectrum (other than intrinsic)'))
            if self.detector.secondary_spectra:
                items = [secSpec.classcode for secSpec in self.detector.secondary_spectra]
            else:
                items = ['UnspecifiedSecondary']
            if self.detector.intrinsic_classcode:
                idx = items.index(self.detector.intrinsic_classcode)
            else:
                idx = 0
            self.combo_selectIntrinsic.addItems(items)
            self.combo_selectIntrinsic.setCurrentIndex(idx)
        else:
            self.noSecondaryRadio.setText(self.tr('No secondary spectrum'))
            self.combo_selectIntrinsic.clear()
        self.label_intrinsicClassCode.setEnabled(checked)
        self.combo_selectIntrinsic.setEnabled(checked)

    def changeIntrinsicText(self, base_spectra=None):
        if base_spectra is None:
            self.label_intrinsicWarning.setVisible(False)
            return
        for spec in base_spectra:
            if spec.material.include_intrinsic:
                self.label_intrinsicWarning.setVisible(True)
                return
        self.label_intrinsicWarning.setVisible(False)

    @Slot(bool)
    def on_btnCreateShieldSpec_clicked(self, checked):
        dialog = CreateShieldedSpectraDialog(self, self.detector.name)
        dialog.exec_()
        self.modelBSL.update_fromdetector(self.detector.name)

    @Slot(bool)
    def on_btnRemoveBaseSpectra_clicked(self, checked):
        """
        Removes loaded Base Spectra
        """
        self.modelBSL.reset_data()
        self.combo_typesecondary.setCurrentIndex(1)
        self.setBackgroundIsoCombo(False)
        self.combo_basesecondary.clear()
        if self.detector is not None:
            self.model.delete_relations()
        self.model.set_ecal([0.0, 0.0, 0.0, 0.0])
        self.model.set_chan_count()
        self.includeSecondarySpectrumCheckBox.setEnabled(False)
        self.noSecondaryRadio.setChecked(True)
        self.reinitialize_combotypesecondary()
        self.changeIntrinsicText()
        self.checkAddIntrinsic.setChecked(False)
        self.checkAddIntrinsic.setEnabled(False)
        self.set_neutrons_display()

    def reinitialize_combotypesecondary(self):
        if self.combo_typesecondary.count() < 3:
            self.combo_typesecondary.addItem(self.tr('Use secondary defined in base spectra files'))

    @Slot(bool)
    def on_btnAddBaseSpectra_clicked(self, checked, dlg = None):
        """
        Loads base spectra
        :param dlg: optional BaseSpectraDialog input
        """
        dialog = dlg
        if dialog is None:
            dialog = BaseSpectraDialog()
            dialog.exec_()
        if dialog.baseSpectra:
            self.reinitialize_combotypesecondary()

            self.newBaseSpectra = dialog.baseSpectra
            self.model.assign_spectra(dialog.model)

            # set base spectra list
            self.modelBSL.add_spectra(self.detector.base_spectra)

            # initialize newBackgroundSpectrum
            self.newBackgroundSpectrum = dialog.backgroundSpectrum  # auto-grabs the first secondary
            self.includeSecondarySpectrumCheckBox.setEnabled(True)  # enable regardless of if there is a secondary or not
            if self.detector.secondary_spectra or self.newBackgroundSpectrum:
                self.checkAddIntrinsic.setEnabled(True)
            else:
                self.checkAddIntrinsic.setEnabled(False)
                self.combo_typesecondary.removeItem(secondary_type['file'])
            # if there are no officially designated secondaries, set the default secondary to the
            # secondary_spectra object for long-term preservation
            if self.newBackgroundSpectrum and not self.detector.secondary_spectra:
                self.model.append_secondaryspec([SecondarySpectrum(
                                            filename=self.newBackgroundSpectrum.filename,
                                            baseCounts=self.newBackgroundSpectrum.baseCounts,
                                            counts=self.newBackgroundSpectrum.counts,
                                            realtime=self.newBackgroundSpectrum.realtime,
                                            livetime=self.newBackgroundSpectrum.livetime,
                                            ecal=self.newBackgroundSpectrum.ecal,
                                            material=self.newBackgroundSpectrum.material,
                                            classcode='UnspecifiedSecondary',
                                            spectrum_type='secondary_spectrum')])
            if self.newBackgroundSpectrum is None:
                self.noSecondaryRadio.setChecked(True)
            else:
                self.internal_secondary = dialog.backgroundSpectrum.material.name  # cosmetic
            self.noSecondaryRadio.setChecked(True)
            if self.newBackgroundSpectrum is not None:
                self.model.append_bgndspec(self.newBackgroundSpectrum)
                self.internal_secondary = dialog.backgroundSpectrum.material.name
                self.secondaryIsBackgroundRadio.setChecked(True)
                self.combo_typesecondary.setEnabled(True)
                self.setDefaultSecondary(sorted([baseSpec.material.name for baseSpec in dialog.baseSpectra]))
            self.changeIntrinsicText(self.newBaseSpectra)
        self.set_neutrons_display()

    # @Slot(bool)
    # def on_btnImportInfluences_clicked(self, checked):
    #     """
    #     Imports Influences
    #     """
    #     filepath = QFileDialog.getOpenFileName(self, 'Distortion File', self.settings.getDataDirectory())[0]
    #     if filepath:
    #         self.tblInfluences.clearContents()
    #         self.detectorInfluences = importDistortionFile(filepath)
    #         for row, detInf in enumerate(self.detectorInfluences):
    #             self.tblInfluences.setItem(row, 0, QTableWidgetItem(detInf[0]))
    #             self.tblInfluences.setItem(row, 1, QTableWidgetItem(str(detInf[1][0])))
    #             self.tblInfluences.setItem(row, 2, QTableWidgetItem(str(detInf[1][1])))
    #             self.tblInfluences.setItem(row, 3, QTableWidgetItem(str(detInf[1][2])))

    def set_neutrons_display(self):
        # set neutron display
        if any([s.neutron_sensitivity for s in self.detector.base_spectra]):
            self.neutrons_label.setText("Base spectra contain neutrons")
            backgrounds = [s for s in self.detector.base_spectra if "bgnd" in s.material.name.lower()]
            if backgrounds:
                bg = backgrounds[0]
                if abs(bg.neutron_sensitivity) < 0.001 or abs(bg.neutron_sensitivity) >= 1000:
                    format_neut_rate = f"{bg.neutron_sensitivity:.3e}"  # Scientific notation
                else:
                    format_neut_rate = f"{bg.neutron_sensitivity:.3f}"  # Up to 3 decimal points
                self.neutrons_label.setText(f"BG neutron detection rate: {format_neut_rate} nps")
        else:
            self.neutrons_label.setText("")
    @Slot(bool)
    def on_btnNewReplay_clicked(self, checked, dialog=None):
        """
        Adds new replay
        """
        if dialog is None:
            dialog = ReplayDialog(self)
            dialog.exec_()
        self.refresh_replays()

    def refresh_replays(self):
        self.replay_tbl_model.update_data(replays=self.session.query(Replay).all(),
                                          detector=self.detector)

    def setBackgroundIsoCombo(self, switch=False):
        self.label_basesecondary.setEnabled(switch)
        self.combo_basesecondary.setEnabled(switch)

    def setSecondarySpecEnable(self, checked=False):
        self.combo_typesecondary.setEnabled(checked)
        self.label_secondarydwell.setEnabled(checked)
        self.spinBox_secondarydwell.setEnabled(checked)
        self.label_resample.setEnabled(checked)
        self.cb_resample.setEnabled(checked)
        if checked:
            self.setBackgroundIsoCombo(self.combo_typesecondary.currentIndex() == secondary_type['base_spec'])
            setattr(self.model, 'detector_type_secondary',
                    self.secondarymap_indexes[self.combo_typesecondary.currentIndex()])
            self.enableComboBase(self.combo_typesecondary.currentIndex())
            if self.detector is not None:
                self.cb_resample.setChecked(self.detector.bckg_spectra_resample if
                                        self.detector.bckg_spectra_resample is not None else True)
                dwell_time = 0 if self.detector.bckg_spectra_dwell is None else self.detector.bckg_spectra_dwell
                self.spinBox_secondarydwell.setValue(dwell_time)
        else:
            self.setBackgroundIsoCombo(False)

    def enableComboBase(self, comboindex):
        self.combo_basesecondary.clear()  # TODO: remove; is this necessary? In master
        if comboindex == secondary_type['base_spec']:
            self.setBackgroundIsoCombo(True)
            self.populateComboBase([item for item in self.modelBSL.bs_list])
            if self.detector and len(self.detector.bckg_spectra):
                self.combo_basesecondary.setCurrentText(self.detector.bckg_spectra[0].material_name)
            else:
                self.setDefaultSecondary([item for item in self.modelBSL.bs_list])
        elif comboindex == secondary_type['file']:
            self.setBackgroundIsoCombo(True)
            # self.setBackgroundIsoCombo(len(self.secondary_spectra) > 1)
            self.populateComboBase([s.classcode for s in self.detector.secondary_spectra])
            if self.detector and self.detector.secondary_classcode:
                self.combo_basesecondary.setCurrentIndex(self.combo_basesecondary.findText(self.detector.secondary_classcode))
                if self.combo_basesecondary.currentIndex() == -1:
                    self.combo_basesecondary.setCurrentIndex(0)
        else:
            self.setBackgroundIsoCombo(False)

    def populateComboBase(self, isotopes):
        self.combo_basesecondary.addItems(isotopes)

    def setDefaultSecondary(self, isotopes):
        for bgndisotope in ['Bgnd', 'Bgnd-Lab', 'NORM', 'NORM-Lab']:
            if bgndisotope in isotopes:
                self.combo_basesecondary.setCurrentIndex(self.combo_basesecondary.findText(bgndisotope))
                break

    @Slot()
    def on_btnExportDetector_clicked(self, savefilepath=None):
        if savefilepath is None:
            savefilepath = QFileDialog.getSaveFileName(self, self.tr('Export Detector'),
                                                       self.settings.getDataDirectory(), filter='*.yaml')[0]
        if savefilepath:
            self.model.export_to_file(savefilepath)

    def enable_export(self):
        self.btnExportDetector.setEnabled(self.txtDetector.text() != '')

    @Slot()
    def on_btnImportDetector_clicked(self, importfilepath=None):
        if importfilepath is None:
            importfilepath = QFileDialog.getOpenFileName(self, self.tr('Import Detector'),
                                                         self.settings.getDataDirectory(), filter='*.yaml')[0]
        if importfilepath:
            self.model.import_from_file(importfilepath)
            self.reinitialize_combotypesecondary()
            self.populate_gui_from_detector(self.detector.name)
            self.refresh_replays()
            # self.model.update_detector()

    @Slot()
    def accept(self):
        self.handleEditingFinished()
        while self.detector.name is None or self.detector.name == '':
            name, ok = QInputDialog.getText(self, self.tr('Detector Name'),
                                            self.tr('Detector Unique Name:'))
            if not ok:
                return
            if not name:
                QMessageBox.critical(self, self.tr('No detector name provided'),
                                     self.tr('User must provide a unique detector name'))
                return
            if self.model.check_database_duplicates():
                QMessageBox.critical(self, self.tr('Detector name already in database'),
                                     self.tr('Detector name already in database,\nPlease specify a different detector name'))
                continue
            self.txtDetector.setText(name)
            self.handleEditingFinished()
        # TODO: Fix, when making a new detector and selecting a replay tool it says it's already
        #  in the database regardless of if it is or not
        if self.model.check_database_duplicates():
            QMessageBox.critical(self, self.tr('Detector name already in database'),
                                 self.tr('Detector name already in database,'
                                                    '\nPlease specify a different detector name'))
            return
        self.model.append_influences(self.modelINL.influences)
        built = self.model.accept()
        if built:
            return QDialog.accept(self)
        else:
            return

    @Slot()
    def reject(self):
        self.model.rollback()
        return QDialog.reject(self)


    class InfluenceDelegate(QItemDelegate):
        def __init__(self, tblInfluence, parent=None):
            QItemDelegate.__init__(self, parent)
            self.tblInfluences = tblInfluence

        def createEditor(self, parent, option, index):
            takenInfluences = []
            for row in range(self.tblInfluences.rowCount()):
                item = self.tblInfluences.item(row, 0)
                if item:
                    takenInfluences.append(item.text())
            comboBox = QComboBox(parent)
            comboBox.setEditable(True)
            comboBox.setValidator(QRegularExpressionValidator(QRegularExpression('[a-zA-Z0-9_.-]+')))
            session = Session()
            for influence in session.query(Influence):
                if influence.name not in takenInfluences:
                    comboBox.addItem(influence.name)
            return comboBox


    class FloatLineDelegate(QItemDelegate):
        def __init__(self, parent):
            QItemDelegate.__init__(self, parent)

        def createEditor(self, parent, option, index):
            lineEdit = QLineEdit(parent)
            lineEdit.setValidator(QDoubleValidator())
            return lineEdit


class DetectorModel(QAbstractItemModel):
    def __init__(self, detector_name=None, *args, **kwargs):
        super(DetectorModel, self).__init__(*args, **kwargs)
        self.detector = Detector()  #detector
        # Assuming the class variables define the columns
        self.column_names = [column.name for column in self.detector.__table__.columns]
        self.column_dict = self.set_column_dict()
        self.editDetector = False
        if 'edit' in kwargs and kwargs['edit'] == '1':
            self.editDetector = True
        self.no_secondary = False
        self.detector_type_secondary = 'base_spec'
        self.base_secondary = ''
        self.detector_names = []
        self._rolledback = False
        self.get_db_detnames(detector_name)
        self.reinitialize_detector(detector_name)
        if not self.detector.name and detector_name is not None:
            self.detector.name = detector_name
        self.set_ecal()

    ########################################################

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 1  # Single row for the class instance

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        # Assuming the class variables define the columns
        return len(self.detector.__table__.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        attribute_values = [getattr(self.detector, column) for column in self.column_names]
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if attribute_values[col] is None:
                return None
            else:
                return str(attribute_values[col])
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if self._rolledback:
            # stop GUI from trying to modify model anymore (which can cause session crash issues)
            return False
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            setattr(self.detector, self.column_names[index.column()], value)
            self.update_detector()
            return True
        else:
            return False

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid() and row == 0:
            # The parent is the root item (single row for the SQLAlchemy instance)
            parentItem = self.detector
        else:
            return QModelIndex()
        if column < len(parentItem.__table__.columns):
            return self.createIndex(row, column, parentItem)
        return QModelIndex()

    def parent(self, index):
        return QModelIndex()  # Flat structure, no parent

    ########################################################
    def accept(self):
        session = Session()

        if self.detector.name == None:
            logging.exception(self.tr('Unhandled Exception: No detector name'), exc_info=True)
            raise AttributeError
        if not self.editDetector and self.check_database_duplicates():
            logging.exception(self.tr('Unhandled Exception: Detector already in database'), exc_info=True)
            raise AttributeError

        # TODO: make this simpler/more efficient using properties
        include_intrinsic_only = self.no_secondary and self.detector.sample_intrinsic
        try:
            self.detector.includeSecondarySpectrum = secondary_type[self.detector_type_secondary] is not None and \
                                                 (not self.no_secondary or include_intrinsic_only)
        except:
            raise Exception('Defined secondary type is not one of the allowed secondary types (base_spec, file, '
                            'scenario, or None)')
        if self.detector.includeSecondarySpectrum:
            # if there has been a modification to the secondary spectrum of choice
            if len(self.detector.bckg_spectra) == 0:
                background = session.query(BackgroundSpectrum).filter_by(
                    detector_name=self.detector.name).first() or BackgroundSpectrum()
                self.append_bgndspec(background)
            elif self.detector.bckg_spectra[0].detector_name is not None:
                background = session.query(BackgroundSpectrum).filter_by(
                    detector_name=self.detector.name).first()
            else:
                background = self.detector.bckg_spectra[0]

            if self.detector_type_secondary == 'base_spec':
                for i, spec in enumerate(self.detector.base_spectra):
                    if not self.base_secondary:
                        base_secondary_names = ['background', 'bgnd', 'bckg']
                    else:
                        base_secondary_names = [self.base_secondary.lower()]
                    if i == 0 or spec.material.name.lower() in base_secondary_names:
                        background.counts = spec.counts
                        background.filename = spec.filename
                        background.livetime = spec.livetime
                        background.ecal     = spec.ecal
                        background.ecal0    = spec.ecal0
                        background.ecal1    = spec.ecal1
                        background.ecal2    = spec.ecal2
                        background.ecal3    = spec.ecal3
                        background.material = spec.material
                        background.material_name = spec.material_name
                        background.realtime = spec.realtime
                        background.metadata = spec.metadata
                        if spec.material.name.lower() in base_secondary_names:
                            break
            elif self.detector_type_secondary == 'file':
                bgnd = [k for k in self.detector.secondary_spectra if k.classcode ==
                        self.base_secondary][0]
                if not bgnd:
                    raise Exception(self.tr('Error: should not be able to select '
                                                   'a material type not in secondary spectra list'))
                self.detector.bckg_spectra.clear()
                self.detector.bckg_spectra.append(self._map_secondary_to_bgnd(bgnd))
            elif self.detector_type_secondary == 'scenario':
                self.detector.bckg_spectra.clear()
                # self.detector.bckg_spectra.append(None)
            if include_intrinsic_only:
                self.detector.secondary_type = None
                self.detector.secondary_classcode = self.detector.intrinsic_classcode
            else:
                self.detector.secondary_type = secondary_type[self.detector_type_secondary]
                if self.detector_type_secondary == 'base_spec':
                    self.detector.secondary_classcode = self.detector.bckg_spectra[0].classcode
                elif self.detector_type_secondary == 'file':
                    self.detector.secondary_classcode = self.base_secondary

        for bg in session.query(BackgroundSpectrum).filter_by(detectors=None).all():
            session.delete(bg)  # delete any non-attached bckg spectra (happens during clear and append above).
        if not self.editDetector:
            session.add(self.detector)
        session.commit()
        return True

    def set_column_dict(self):
        return dict(zip(self.column_names, range(len(self.column_names))))

    def check_database_duplicates(self):
        if self.detector.name in self.detector_names:
            return True
        return False

    def _map_secondary_to_bgnd(self, spec=None):
        """
        Utility function for table class conversion
        (Note for future development: is BackgroundSpectrum strictly necessary,
        or can we get away with just using SecondarySpectrum?)
        """
        if spec is None:
            return
        b = BackgroundSpectrum()
        for m in [k for k in dir(spec) if not callable(getattr(spec, k)) and not k.startswith("_")
                  and not k in ['id', 'spectrum_type', 'detector_name', 'detectors']]:
            if m in dir(b):
                setattr(b, m, getattr(spec, m))
        return b

    def get_db_detnames(self, current_name=None):
        """
        Gets the names of all the detectors in the database at the beginning of the edit such that
        @return:
        """
        session = Session()
        detectors = session.query(Detector).all()
        if len(detectors):
            if current_name:
                self.detector_names = [k.name for k in detectors if k.name != current_name]
            else:
                self.detector_names = [k.name for k in detectors]

    def update_detector(self):
        self.dataChanged.emit(self.index(0, 0), self.index(0, self.columnCount() - 1))

    def reinitialize_detector(self, detector_name=None):
        if detector_name:
            edit_detector = Session().query(Detector).filter_by(name=detector_name).first()
            if edit_detector is not None:
                self.detector = edit_detector
                self.editDetector = True
                self.update_detector()
                return True
            return False
        return False

    def assign_spectra(self, bscmodel=None):
        """
        Utility function capturing all the assignments from base spectra files.
        Current code will overwrite ecal and channel count if the user loads in a second set of
        spectra from a different directory.
        @param bscmodel: BaseSpectraLoadModel
        @return:
        """
        if bscmodel:
            self.append_basespec(bscmodel.baseSpectra)
            self.append_secondaryspec(bscmodel.secondary_spectra)
            self.set_ecal(bscmodel.ecal)
            self.set_chan_count(bscmodel.channel_count)

    def append_basespec(self, basespec):
        try:
            for spec in basespec:
                self.detector.base_spectra.append(spec)
        except:  # if not an iterable
            self.detector.base_spectra.append(basespec)
        # self.update_detector()

    def append_secondaryspec(self, secondaryspec):
        try:
            for spec in secondaryspec:
                self.detector.secondary_spectra.append(spec)
        except:  # if not an iterable
            self.detector.secondary_spectra.append(secondaryspec)
        # self.update_detector()

    def append_bgndspec(self, bgndspec):
        self.detector.bckg_spectra.clear()
        self.detector.bckg_spectra.append(bgndspec)
        # self.update_detector()

    def append_influences(self, influences: list):
        """
        @param influences: a list of strings (influence names) which must be parsed from session
        @return:
        """
        session = Session()
        self.detector.influences.clear()
        for infl_name in influences:
            influence = session.query(Influence).filter_by(name=infl_name).first()
            self.detector.influences.append(influence)
        # self.update_detector()

    def set_replay(self, replay_name):
        """
        Set the detector replay tool from the replay tool name. Breaks if the user passes a
        replay tool that doesn't exist
        @param replay_name: string
        @return:
        """
        replay = Session().query(Replay).filter(Replay.name==replay_name).first()
        if not replay and replay_name:
            raise ValueError(self.tr('No replay by the name of {}').format(replay_name))
        self.detector.add_replay(replay)

    def delete_relations(self):
        session = Session()
        for spec in session.query(Spectrum).filter(
                Spectrum.detector_name == self.detector.name).all():
            session.delete(spec)
        if self.detector.base_spectra is not None:
            self.detector.base_spectra.clear()
        if self.detector.secondary_spectra is not None:
            self.detector.secondary_spectra.clear()
        if self.detector.bckg_spectra is not None:
            self.detector.bckg_spectra.clear()
        self.update_detector()

    # The following are all called on an API basis\
    def set_chan_count(self, counts=None):
        if counts is not None:
            self.setData(self.index(0, self.column_dict['chan_count']), int(counts))

    def set_chan_count_from_spectrum(self, counts: str = None):
        self.detector.chan_count = int(counts.count(',') + 1) if counts else None
        self.update_detector()

    def set_ecal(self, ecal: list = None):
        if ecal is None:
            ecal = [self.detector.ecal0, self.detector.ecal1, self.detector.ecal2, self.detector.ecal3]
        ecal = [k if k is not None else 0.0 for k in ecal]
        for i, v in enumerate(ecal):
            self.detector.__setattr__(f'ecal{i}', float(v))
        for i in range(len(ecal), 4):
            self.detector.__setattr__(f'ecal{i}', 0.0)
        self.update_detector()

    def set_sample_intrinsic(self, sample_intrinsic=False):
        self.setData(self.index(0, self.column_dict['sample_intrinsic']), sample_intrinsic)

    def set_intrinsic_classcode(self, intrinsic_classcode=''):
        if intrinsic_classcode:
            self.setData(self.index(0, self.column_dict['intrinsic_classcode']), intrinsic_classcode)

    def set_bgnd_spec_resample(self, resample=True):
        self.setData(self.index(0, self.column_dict['bckg_spectra_resample']), resample)

    def set_bgnd_spec_dwell(self, dwell=0.):
        try:
            self.setData(self.index(0, self.column_dict['bckg_spectra_dwell']), float(dwell))
        except:
            self.setData(self.index(0, self.column_dict['bckg_spectra_dwell']), 0)

    def set_detector_params(self, txtManufacturer=None, txtInstrumentId=None, txtClassCode=None,
                            txtHardwareVersion=None, replays=[], resultsTranslator=None):
        self.detector.manufacturer = txtManufacturer
        self.detector.instr_id = txtInstrumentId
        self.detector.class_code = txtClassCode
        self.detector.hardware_version = txtHardwareVersion
        for replay in replays:
            self.detector.add_replay(replay)
        self.detector.resultsTranslator = resultsTranslator

    def import_from_file(self, importfilepath=None):
        """
        Loads a detector from an import .yaml file
        @param importfilepath:
        @return:
        """
        if importfilepath:
            with open(importfilepath, 'r') as file:
                importdict = yaml.safe_load(file)
            self.import_from_dict(importdict)

    def import_from_dict(self, importdict=None):
        """
        Loads a detector from an import dictionary
        @param importdict:
        @return:
        """
        if importdict:
            dschema = DetectorSchema()
            session = Session()
            while session.query(Detector).filter_by(name=importdict['name']).first():
                importdict['name'] += self.tr('_Imported')
            if importdict['replays']:
                for i, replay in enumerate(importdict['replays']):
                    while session.query(Replay).filter_by(name=replay['name']).first() or (replay['name'] in [
                                r['name'] for r in [v for j, v in enumerate(importdict['replays']) if j != i]]):
                        replay['name'] += self.tr('_Imported')
            self.detector = dschema.load(importdict, session=session)
            if self.detector.chan_count == -1:
                self.detector.chan_count = ''
            self.editDetector = True
            session.add(self.detector)
            self.update_detector()

    def export_to_file(self, savefilepath=None):
        """
        Export a detector to a .yaml file
        @param exportfilepath:
        @return:
        """
        if savefilepath:
            dschema = DetectorSchema()
            if not self.detector.chan_count:
                self.detector.chan_count = -1
            exportstring = dschema.dump(self.detector)
            with open(savefilepath,'w') as file:
                yaml.dump(exportstring, file)
            # Check to make sure our exported detector is viable
            session = Session()
            detectorimport = dschema.load(exportstring, session=session)

    def rollback(self):
        session = Session()
        session.rollback()
        session.commit()
        self._rolledback = True


class InfluenceListModel(QAbstractListModel):

    def __init__(self, data=None,  *args, **kwargs):
        """
        @param data: a list of influence names
        @param args:
        @param kwargs:
        """
        super(InfluenceListModel, self).__init__(*args, **kwargs)
        self.influences = data or []

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self.influences.clear()
        self.layoutChanged.emit()

    def add_influences(self, new_influences):
        self.layoutAboutToBeChanged.emit()
        if type(new_influences) == str:
            self.influences.append(new_influences)
        elif len(new_influences) and type(new_influences[0]) == str:
            self.influences = sorted(new_influences)
        else:
            self.influences = sorted([influence.name for influence in new_influences])
        self.layoutChanged.emit()

    def remove_influence(self, index):
        self.layoutAboutToBeChanged.emit()
        self.influences.pop(index.row())
        self.layoutChanged.emit()

    def rowCount(self, index=None):
        return len(self.influences)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.influences[index.row()]


class ReplayTableModel(QAbstractTableModel):
    def __init__(self, detector, replays, *args, **kwargs):
        super(ReplayTableModel, self).__init__(*args, **kwargs)
        self.replays = replays
        self.detector = detector
        self.headers = [' ', self.tr('Replay'), self.tr('Replay Settings')]

    def rowCount(self, parent=QModelIndex()):
        return len(self.replays)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        replay = self.replays[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 1:
                return replay.name
            elif index.column() == 2:
                return replay.settings_str_u()
        elif role == Qt.CheckStateRole:
            if index.column() == 0:
                return Qt.Checked if self.detector in self.replays[index.row()].detectors else Qt.Unchecked

    def setData(self, index, value, role=Qt.DisplayRole):
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole:
            if index.column() == 0:
                if bool(value):
                    self.replays[index.row()].add_to_detector(self.detector)
                else:
                    self.replays[index.row()].remove_from_detector(self.detector)
                self.dataChanged.emit(index, index, [Qt.CheckStateRole])
                return True
        return False

    def update_data(self, replays, detector):
        self.beginResetModel()
        self.replays = replays
        self.detector = detector
        self.endResetModel()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
        return None




