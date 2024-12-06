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
This module allows the user to select replay and results translator executables
as well as the translator template
"""
import numpy as np
import pandas as pd
from PySide6.QtCore import Slot, Qt, QModelIndex, QAbstractTableModel, QRegularExpression, QSize, \
    QCoreApplication
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QItemDelegate, QLineEdit, \
    QTableView, QSizePolicy, QDialogButtonBox, QVBoxLayout
from src.qt_utils import RegExpValidator
from src.rase_settings import RaseSettings
from src.rase_functions import get_DRFList_from_webid
from src.table_def import Replay, Session, ReplayTypes, ConfidenceTypes
from src.ui_generated import ui_new_replay_dialog

# translation_tag = 'rep_d'


class ReplayDialog(ui_new_replay_dialog.Ui_ReplayDialog, QDialog):
    def __init__(self, parent, replay=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setupUi(self)
        self.settings = RaseSettings()
        self.cmbDRFs.addItems(self.settings.getWebIDDRFsList())
        self.stack.setCurrentIndex(0)
        self.enable_confidences(self.cbConfUse.isChecked())
        self.cbConfUse.toggled.connect(lambda x: self.enable_confidences(x))
        self.radioStandalone.toggled.connect(lambda x: self.stack.setCurrentIndex(0) if x else None)
        self.radioWeb.toggled.connect(lambda x: self.stack.setCurrentIndex(1) if x else None)
        self.radioConfDisc.toggled.connect(lambda x: self.btnConfDisc.setEnabled(x and self.cbConfUse.isChecked()))
        self.radioConfCont.toggled.connect(lambda x: self.btnConfCont.setEnabled(x and self.cbConfUse.isChecked()))
        self.btnConfDisc.clicked.connect(lambda: self.define_confidences('discrete'))
        self.btnConfCont.clicked.connect(lambda: self.define_confidences('continuous'))

        self.replay = ReplayModel(replay)

        if replay:
            self.radioStandalone.setChecked(replay.type == ReplayTypes.standalone)
            self.radioWeb.setChecked(replay.type == ReplayTypes.gadras_web)
            self.setWindowTitle(self.tr('Edit Replay Software'))
            self.txtName.setText(replay.name)
            self.txtCmdLine.setText(replay.exe_path)
            self.txtSettings.setText(replay.settings)
            self.cbCmdLine.setChecked(bool(replay.is_cmd_line))
            self.txtTemplatePath.setText(replay.n42_template_path)
            self.txtFilenameSuffix.setText(replay.input_filename_suffix)
            self.txtWebAddress.setText(replay.web_address)
            index = self.cmbDRFs.findText(replay.drf_name)
            self.cmbDRFs.setCurrentIndex(index) if index >=0 else self.cmbDRFs.setCurrentIndex(0)
            self.cbConfUse.setChecked(replay.use_confidence)
            self.radioConfDisc.setChecked(replay.confidence_mode == ConfidenceTypes.discrete)
            self.radioConfCont.setChecked(replay.confidence_mode == ConfidenceTypes.continuous)
            if replay.translator_exe_path:
                self.txtResultsTranslator.setText(replay.translator_exe_path)
                self.txtSettings_3.setText(replay.translator_settings)
                self.cbCmdLine_3.setChecked(bool(replay.translator_is_cmd_line))
            self.txtAssociatedDetectors.setText(self.tr(f'This replay is associated with the following detectors: ') +
                                                f'{", ".join([d.name for d in replay.detectors])}')

        self.lineedits = {self.txtName: 'name', self.txtCmdLine: 'exe_path',
                     self.txtSettings: 'settings', self.txtTemplatePath: 'n42_template_path',
                     self.txtFilenameSuffix: 'input_filename_suffix', self.txtWebAddress: 'web_address',
                     self.txtResultsTranslator: 'translator_exe_path', self.txtSettings_3: 'translator_settings'}
        self.checkboxes = {self.cbCmdLine: 'is_cmd_line', self.cbCmdLine_3: 'translator_is_cmd_line',
                           self.cbConfUse: 'use_confidence'}


    @Slot(bool)
    def enable_confidences(self, checked):
        self.radioConfDisc.setEnabled(checked)
        if self.radioConfDisc.isChecked() and self.radioConfDisc.isEnabled():
            self.btnConfDisc.setEnabled(True)
        else:
            self.btnConfDisc.setEnabled(False)
        self.radioConfCont.setEnabled(checked)
        if self.radioConfCont.isChecked() and self.radioConfCont.isEnabled():
            self.btnConfCont.setEnabled(True)
        else:
            self.btnConfCont.setEnabled(False)

    @Slot(bool)
    def on_btnBrowseExecutable_clicked(self, checked):
        """
        Selects Replay executable
        """
        filepath = QFileDialog.getOpenFileName(self, QCoreApplication.translate('rep_d',
                                        'Path to Replay Tool'), self.settings.getDataDirectory())[0]
        if filepath:
            self.txtCmdLine.setText(filepath)

    @Slot(bool)
    def on_btnBrowseTranslator_clicked(self, checked):
        """
        Selects Translator Template
        """
        filepath = QFileDialog.getOpenFileName(self, QCoreApplication.translate('rep_d',
                                        'Path to n42 Template'), self.settings.getDataDirectory())[0]
        if filepath:
            self.txtTemplatePath.setText(filepath)

    @Slot(bool)
    def on_btnBrowseResultsTranslator_clicked(self, checked):
        """
        Selects Results Translator Executable
        """
        filepath = QFileDialog.getOpenFileName(self, QCoreApplication.translate('rep_d',
                          'Path to Results Translator Tool'), self.settings.getDataDirectory())[0]
        if filepath:
            self.txtResultsTranslator.setText(filepath)

    @Slot(bool)
    def on_btnUpdateDRFList_clicked(self, checked):
        """
        Obtain the List of DRFs from WebID
        """
        url = self.txtWebAddress.text().strip('/')
        drfList = get_DRFList_from_webid(url)
        if drfList:
            currentDRF = self.cmbDRFs.currentText()
            # remove 'auto' options since RASE does not pass n42s w/ instrument specifications
            if 'auto' in drfList:
                drfList.remove('auto')
            self.settings.setWebIDDRFsList(drfList)
            self.cmbDRFs.clear()
            self.cmbDRFs.addItems(self.settings.getWebIDDRFsList())
            index = self.cmbDRFs.findText(currentDRF)
            self.cmbDRFs.setCurrentIndex(index) if index >=0 else self.cmbDRFs.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, self.tr('Connection error'),
                                self.tr('Error while connecting to Full Spectrum Web ID. Is the web address correct?'))

    def set_all_values(self):
        for k, v in self.lineedits.items():
            self.replay.__setattr__(v, k.text())
        for k, v in self.checkboxes.items():
            self.replay.__setattr__(v, k.isChecked())
        self.replay.drf_name = self.cmbDRFs.currentText()
        self.replay.set_replay_types(self.stack.currentIndex())
        self.replay.set_confidence_types(0 if self.radioConfDisc.isChecked() else 1)

    def define_confidences(self, mode='discrete'):
        if mode == 'discrete':
            # backup_data = self.replay.confidence_scale_map.copy(deep=True)
            model = ConfidenceTableModel(self.replay.confidence_scale_map)
            backup_data = model.model_data.copy(deep=True)
            if self.create_conftable_gui(mode, model):
                model.sort_columns()
                self.replay.confidence_scale_map = model.model_data.set_index('Reported')['Weight'].to_dict()
            else:
                self.replay.confidence_scale_map = backup_data.set_index('Reported')['Weight'].to_dict()
        else:
            model = ConfidenceTableModel(self.replay.confidence_scale_range)
            backup_data = model.model_data.copy(deep=True)
            if self.create_conftable_gui(mode, model):
                model.sort_columns('continuous')
                self.replay.confidence_scale_range = [model.model_data['Reported'].tolist(),
                                                      model.model_data['Weight'].tolist()]
            else:
                self.replay.confidence_scale_range = [backup_data['Reported'].tolist(),
                                                      backup_data['Weight'].tolist()]

    def create_conftable_gui(self, mode, model):
        dialog = QDialog(parent=self)
        dialog.setObjectName('dialogConfidence')
        tableview = QTableView(dialog)
        tableview.setObjectName(u'tblConfidence')
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHeightForWidth(tableview.sizePolicy().hasHeightForWidth())
        tableview.setSizePolicy(sizePolicy1)
        tableview.setMinimumSize(QSize(440, 0))
        tableview.setShowGrid(True)
        tableview.setGridStyle(Qt.SolidLine)
        tableview.horizontalHeader().setMinimumSectionSize(140)
        tableview.horizontalHeader().setStretchLastSection(True)
        tableview.verticalHeader().setVisible(False)
        tableview.verticalHeader().setCascadingSectionResizes(True)
        tableview.setModel(model)
        tableview.setItemDelegate(ConfidenceTableDelegate(model, mode))
        # button box
        buttonBox = QDialogButtonBox(dialog)
        buttonBox.setObjectName(u"buttonBox")
        buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        # layout
        layout = QVBoxLayout(dialog)
        layout.addWidget(tableview)
        layout.addWidget(buttonBox)
        dialog.resize(430, 250)
        dialog.setWindowTitle(self.tr('Setting {} confidence values.').format(mode))
        return dialog.exec_()

    @Slot()
    def accept(self):
        self.set_all_values()
        error_message = self.replay.accept()
        if error_message is not None:
            if error_message[0] == 'critical':
                QMessageBox.critical(self, error_message[1], error_message[2])
                return
            elif error_message[0] == 'warning':
                QMessageBox.warning(self, error_message[1], error_message[2])
                return
        return QDialog.accept(self)


class ReplayModel(Replay):
    def __init__(self, replay=None, *args, **kwargs):
        super(ReplayModel, self).__init__(*args, **kwargs)
        self.set_default_values(kwargs.get('name') if 'name' in kwargs.keys() else '')
        self.settable_attributes = sorted(set([key for key in self.__dict__.keys()]).intersection(
                                          set([r.name for r in Replay.__table__.columns])))
        if replay:
            self.__dict__.update(replay.__dict__)
            self.orig_name = replay.name

    def set_default_values(self, name=''):
        self.name = name
        self.orig_name = name
        self.type = ReplayTypes.standalone
        self.exe_path = ''
        self.is_cmd_line = True
        self.settings = 'INPUTDIR OUTPUTDIR'
        self.n42_template_path = ''
        self.input_filename_suffix = '.n42'
        self.web_address = 'https://full-spectrum.sandia.gov/'
        self.drf_name = 'auto'
        self.translator_exe_path = ''
        self.translator_is_cmd_line = True
        self.translator_settings = 'INPUTDIR OUTPUTDIR'
        self.use_confidence = False
        self.confidence_mode = ConfidenceTypes.discrete
        self.confidence_scale_map = self.confidence_scale_default_map
        self.confidence_scale_range = self.confidence_scale_default_range

    def set_replay_types(self, rtype):
        """
        Utility function
        @param rtype: integer (0 or 1) or string ('standalone' or 'gadras_web')
        @return:
        """
        if rtype == 0 or rtype == 'standalone':
            self.type = ReplayTypes.standalone
        else:
            self.type = ReplayTypes.gadras_web

    def set_confidence_types(self, rtype):
        """
        Utility function
        @param rtype: integer (0 or 1) or string ('standalone' or 'gadras_web')
        @return:
        """
        if rtype == 0 or rtype == 'discrete':
            self.confidence_mode = ConfidenceTypes.discrete
        else:
            self.confidence_mode = ConfidenceTypes.continuous

    def accept(self):
        if not self.name:
            return (QCoreApplication.translate('rep_d', 'critical'),
                    QCoreApplication.translate('rep_d', 'Insufficient Information'),
                    QCoreApplication.translate('rep_d', 'Must specify a replay tool name'))
        session = Session()
        replay = session.query(Replay).filter_by(name=self.name).first()
        # if we are trying to name our RT with a name that already exists for another RT
        if replay and not self.orig_name == self.name:
            return (QCoreApplication.translate('rep_d', 'warning'),
                    QCoreApplication.translate('rep_d', 'Bad Replay Name'),
                    QCoreApplication.translate('rep_d', 'Replay with this name exists. Specify Different Replay Name'))
        if not replay:
            orig_replay = session.query(Replay).filter_by(name=self.orig_name).first()
            # if we are editing the name of our existing RT
            if orig_replay is not None:
                replay = orig_replay
            # if we are creating a new RT
            else:
                replay = Replay()
                session.add(replay)
        # else: we are editing our replay tool but keeping the name the same
        for k in self.settable_attributes:
            if k == 'id':
                continue
            replay.__setattr__(k, self.__dict__[k])
        session.commit()
        self.id = replay.id
        return (None, None, None)



class ConfidenceTableModel(QAbstractTableModel):
    def __init__(self, data=None, *args, **kwargs):
        """
        @param data: numpy array or list of lists
        @param id: string or None
        @param duplicate_ids: list of strings (ids)
        @param args:
        @param kwargs:
        """
        super(ConfidenceTableModel, self).__init__(*args, **kwargs)
        self._colheaders = [QCoreApplication.translate('rep_d', 'Reported'),
                            QCoreApplication.translate('rep_d', 'Weight')]
        self._data = self._set_empty_data()
        if data is not None:
            self.setDataFromTable(data)

    @property
    def model_data(self):
        return self._data

    def _set_empty_data(self):
        df = pd.DataFrame(np.empty((10, 2), dtype=str), columns=self._colheaders)
        return df

    def setDataFromTable(self, data):
        for row, element in enumerate(data):
            if type(data) == dict:
                self.setData(self.index(row, 0), element)
                self.setData(self.index(row, 1), data[element])
            else:
                for i in range(len(element)):
                    self.setData(self.index(i, row), element[i])

    def rowCount(self, index=None):
        return self._data.shape[0]

    def columnCount(self, index=None):
        return self._data.shape[1]

    def index(self, row, column, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self._data
        else:
            return QModelIndex()
        if column < len(parentItem.columns):
            return self.createIndex(row, column, parentItem)
        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._data.iloc[row, col]

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            return True
        else:
            return False

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        if role == Qt.UserRole:
            if orientation == Qt.Vertical:
                return str(self._data.index[section])

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def sort_columns(self, conftype='discrete'):
        self._data.replace('', np.nan, inplace=True)
        self._data.dropna(inplace=True)
        self._data['Weight'] = pd.to_numeric(self._data['Weight'])
        self._data.sort_values(by=['Weight'], inplace=True)
        self._data.reset_index(drop=True, inplace=True)
        if conftype != 'discrete':
            self._data['Reported'] = pd.to_numeric(self._data['Reported'])
            if self.rowCount() < 2:
                self._data.loc[1] = [self._data.loc[0]['Reported'] + 1, 1]
            else:
                previousval = -1
                maxval = self._data.loc[len(self._data)-1][0]
                rowstokeep = 0
                rows_to_remove = []
                for row in self._data.iterrows():
                    if previousval < 0:
                        previousval = row[1][0]
                        rowstokeep += 1
                        continue
                    if row[1][0] > maxval:
                        rows_to_remove.append(row[0])
                    elif row[1][0] < previousval and rowstokeep >= 2:
                        rows_to_remove.append(row[0])
                    else:
                        rowstokeep += 1
                        previousval = row[1][0]
                self._data.drop(rows_to_remove, inplace=True)
                self._data.reset_index(drop=True, inplace=True)


class ConfidenceTableDelegate(QItemDelegate):
    def __init__(self, parent, mode='discrete'):
        super(ConfidenceTableDelegate, self).__init__(parent)
        self.table = parent
        self.mode = mode
        self.settings = RaseSettings()

    def createEditor(self, parent, option, index):
        if index.column() == 1:
            reg_ex = QRegularExpression(r'^0*(?:1(?:\.0*)?|0(?:\.\d*)?|\.\d+)$')
            return self.customEditor(parent, index, reg_ex)
        elif self.mode == 'continuous':
            reg_ex = QRegularExpression(r'^-?(?:0*(?:1(?:\.0*)?|0(?:\.\d*)?|\.\d+)|(?:[1-9]\d*\.?\d*|\.\d+)|)$')
            return self.customEditor(parent, index, reg_ex)
        else:
            return super(ConfidenceTableDelegate, self).createEditor(parent, option, index)

    def customEditor(self, parent, index, reg_ex):
        editor = QLineEdit(parent)
        editor.setValidator(RegExpValidator(reg_ex, parent))
        return editor

    def setModelData(self, editor, model, index):
        self.table.setData(index, editor.text())


if __name__ == '__main__':
    from src.rase_init import init_rase
    init_rase()

    name = 'testnew'

    session = Session()
    print(len(session.query(Replay).all()))
    replay = ReplayModel()
    replay.name = name
    replay.set_replay_types('standalone')
    replay.is_cmd_line = True
    error = replay.accept()
    if error[0] is not None:
        print(error[1])
        print(error[2])
    print(len(session.query(Replay).all()))

    replayDelete = session.query(Replay).filter(Replay.name == name)
    replayDelete.delete()
    session.commit()
    print(len(session.query(Replay).all()))
