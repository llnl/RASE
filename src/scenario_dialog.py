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
This module allows user to create replay scenario
"""
import re
from itertools import product
import numpy as np
import pandas as pd

from PySide6.QtCore import Slot, QRegularExpression, Qt, QPoint, QAbstractItemModel,\
    QAbstractListModel, QModelIndex, QAbstractTableModel, QItemSelectionModel, QCoreApplication
from PySide6.QtWidgets import QDialog,  QLineEdit, QMessageBox, QItemDelegate, QComboBox, QMenu, \
    QDialogButtonBox, QDataWidgetMapper
from PySide6.QtGui import QRegularExpressionValidator, QStandardItemModel, QStandardItem, \
    QAction, QValidator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from src.qt_utils import DoubleValidator, IntValidator, RegExpValidator
from src.table_def import Session, Influence, ScenarioGroup, Material, ScenarioMaterial, \
    ScenarioBackgroundMaterial, Scenario, Detector, BaseSpectrum
from src.ui_generated import ui_create_scenario_dialog, ui_scenario_range_dialog
from src.rase_functions import check_groups
from src.rase_settings import RaseSettings
from src.scenario_group_dialog import GroupSettings
from src.help_dialog import HelpDialog
from src.neutrons import any_neutrons_in_db

UNITS, MATERIAL, INTENSITY, INTENSITY_NEUTRON = 0, 1, 2, 3
units_labels = {'DOSE': QCoreApplication.translate('scen_d', 'DOSE (\u00B5Sv/h)'),
                'FLUX': QCoreApplication.translate('scen_d', 'FLUX (\u03B3/(cm\u00B2s))')}


def RegExpSetValidator(parent=None, auto_s=False) -> QRegularExpressionValidator:
    """Returns a Validator for the set range format"""
    if auto_s:
        reg_ex = QRegularExpression(r'((\d*\.\d*)|(\d*))')
    else:
        reg_ex = QRegularExpression(
            r'((\d*\.\d+|\d+)-(\d*\.\d+|\d+):(\d*\.\d+|\d+)(((,\d*\.\d+)|(,\d+))*))|(((\d*\.\d+)|(\d+))((,\d*\.\d+)|(,\d+))*)')
    validator = RegExpValidator(reg_ex, parent)
    return validator


class ScenarioDialog(ui_create_scenario_dialog.Ui_ScenarioDialog, QDialog):
    def __init__(self, parent, id=None, duplicate_ids=[]):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setupUi(self)

        self.txtAcqTime.setToolTip(self.tr('Enter comma-separated values OR range as min-max:step OR range followed '
                                           'by comma-separated values'))
        self.txtAcqTime.setValidator(RegExpSetValidator(self.txtAcqTime))
        self.txtAcqTime.validator().validationChanged.connect(self.handle_validation_change)

        self.txtReplication.setValidator(IntValidator(self.txtReplication))
        self.txtReplication.validator().setBottom(1)
        self.txtReplication.validator().validationChanged.connect(self.handle_validation_change)

        self.model = ScenarioModel(id=id, duplicate_ids=duplicate_ids)
        self.modelMat = self.model.modelSource
        self.modelBgnd = self.model.modelBackground
        self.modelInfl = self.model.modelInfluences
        self.tblMaterial.setModel(self.modelMat)
        self.tblBackground.setModel(self.modelBgnd)
        self.lstInfluences.setModel(self.modelInfl)
        self.model_lineedits = [self.txtAcqTime, self.txtReplication, self.txtComment]
        self.tblMaterial.verticalHeader().setVisible(False)
        self.tblBackground.verticalHeader().setVisible(False)
        self.settings = RaseSettings()
        self.model.dataChanged.connect(self.scenarioChanged)  # enables "okay" if valid replication/acq_time
        for m in [self.model, self.modelMat, self.modelBgnd]:
            m.dataChanged.connect(self.updateScenariosList)

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.model)
        self.set_modelmap()
        self.mapper.toFirst()

        self.tblMaterial.setItemDelegate(MaterialDoseDelegate(self.modelMat, unitsCol=UNITS,
                                                  materialCol=MATERIAL, intensityCol=INTENSITY,
                                                  neutronCol=INTENSITY_NEUTRON,
                                                  tables=[self.modelMat, self.modelBgnd]))
        self.tblBackground.setItemDelegate(MaterialDoseDelegate(self.modelBgnd, unitsCol=UNITS,
                                                  materialCol=MATERIAL, intensityCol=INTENSITY,
                                                  neutronCol=INTENSITY_NEUTRON,
                                                  tables=[self.modelMat, self.modelBgnd]))

        self.tblMaterial.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblBackground.setContextMenuPolicy(Qt.CustomContextMenu)
        session = Session()

        self.tblMaterial.customContextMenuRequested.connect(lambda x, table=self.tblMaterial,
                               model=self.modelMat: self.context_auto_range(x, table, model))
        self.tblBackground.customContextMenuRequested.connect(lambda x, table=self.tblBackground,
                               model=self.modelMat: self.context_auto_range(x, table, model))
        for row in range(self.modelMat.rowCount(None)):
            self.tblMaterial.setRowHeight(row, 22)
        for row in range(self.modelBgnd.rowCount(None)):
            self.tblBackground.setRowHeight(row, 22)

        # Make it explicitly source the default detector combobox from model to assure consistency
        self.comboDetectorSelect.addItems([self.modelMat.detector_selection] + [s.name for s in
                                                              session.query(Detector).all()])
        self.comboDetectorSelect.currentIndexChanged.connect(self.updateTableDelegate)
        self.comboDetectorSelect.currentIndexChanged.connect(self.changeDetectorSelect)
        # display a previous scenario if defined
        if id:
            self.setWindowTitle(self.tr('Scenario Edit'))
            for inflidx, infl in enumerate(self.modelInfl.influences):
                influence = session.query(Influence).filter_by(name=infl).first()
                if influence in self.modelInfl.selected_influences:
                    self.lstInfluences.selectionModel().select(
                        self.modelInfl.index(inflidx, 0), QItemSelectionModel.Select)

        self.lstInfluences.selectionModel().selectionChanged.connect(self.handle_influence_select)
        self.txtComment.textChanged.connect(self.scenarioChanged)
        self.txtAcqTime.textChanged.connect(self.scenarioChanged)
        self.txtReplication.textChanged.connect(self.scenarioChanged)

        self.updateScenariosList()

        self.set_neutrons_visible(False)
        if any_neutrons_in_db():
            self.set_neutrons_visible(True)
        if self.modelMat.any_neutrons_in_table() or self.modelBgnd.any_neutrons_in_table():
            self.set_neutrons_visible(True)


    def set_modelmap(self):
        col_names = ['acq_time', 'replication', 'comment']
        for w, c in zip(self.model_lineedits, col_names):
            self.mapper.addMapping(w, self.model.column_dict[c])

    def set_neutrons_visible(self,visible):
        self.tblMaterial.setColumnHidden(INTENSITY_NEUTRON, not visible)
        self.tblBackground.setColumnHidden(INTENSITY_NEUTRON, not visible)

    def get_neutrons_visible(self):
        a = self.tblMaterial.isColumnHidden(INTENSITY_NEUTRON)
        b = self.tblBackground.isColumnHidden(INTENSITY_NEUTRON)
        assert bool(a) == bool(b)
        return not (a and b)

    def handleEditingFinished(self):
        # must grab lineedits at the beginning to make sure that the scenario update doesn't
        # replace the values in the process
        linetexts = [lineedit.text() for lineedit in self.model_lineedits]
        # for scenario model (the line edits)
        for linetext, line_edit in zip(linetexts, self.model_lineedits):
            column = self.model_lineedits.index(line_edit)
            self.model.setData(self.model.index(0, column), linetext, Qt.EditRole)
        # for the table models
        for table, model in zip([self.tblMaterial, self.tblBackground], [self.modelMat, self.modelBgnd]):
            if table.indexWidget(table.currentIndex()) is not None:
                model.setData(table.currentIndex(),
                              table.indexWidget(table.currentIndex()).currentText(), Qt.EditRole)

    def make_matDict(self, mats, m_dict):
        for mat in mats:
            m_dict[mat.material_name].update([mat.dose])
        return m_dict

    @Slot()
    def handle_influence_select(self, index):
        self.modelInfl.setSelectedInfluences([r.row() for r in
                                       self.lstInfluences.selectionModel().selectedIndexes()])

    @Slot(QValidator.State)
    def handle_validation_change(self, state):
        if state == QValidator.Invalid:
            color = 'red'
        elif state == QValidator.Intermediate:
            color = 'gold'
            # need to force this, setData isn't called for intermediate states
            self.model.set_attributes({'acq_time': self.txtAcqTime.text(),
                                       'replication': self.txtReplication.text(),
                                        'comment': self.txtComment.text()})
        elif state == QValidator.Acceptable:
            color = 'green'
        sender = self.sender().parent()
        sender.setStyleSheet(f'border: 2px solid {color}')

    @Slot()
    def scenarioChanged(self):
        """
        Listens for Scenario changed
        Updates an internal flag related to changed scenario
        Enables and Disables OK button if scenario values are acceptable or not
        """
        if self.txtAcqTime.hasAcceptableInput() and self.txtReplication.hasAcceptableInput():
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @Slot(int)
    def updateTableDelegate(self, index):
        if index == 0:
            selected_detname = None
        else:
            selected_detname = self.comboDetectorSelect.currentText()
        self.tblMaterial.setItemDelegate(MaterialDoseDelegate(self.modelMat, unitsCol=UNITS,
                                                  materialCol=MATERIAL, intensityCol=INTENSITY,
                                                  selected_detname=selected_detname,
                                                  tables=[self.modelMat, self.modelBgnd]))
        self.tblBackground.setItemDelegate(MaterialDoseDelegate(self.modelBgnd, unitsCol=UNITS,
                                                  materialCol=MATERIAL, intensityCol=INTENSITY,
                                                  selected_detname=selected_detname,
                                                  tables=[self.modelMat, self.modelBgnd]))

    @Slot(int)
    def changeDetectorSelect(self, index):
        self.modelMat.detector_selection = self.comboDetectorSelect.itemText(index)
        self.modelBgnd.detector_selection = self.comboDetectorSelect.itemText(index)

    @Slot(QPoint)
    def context_auto_range(self, point, table, model):
        index = table.indexAt(point)
        # show the context menu only if on a valid part of the table
        if index.isValid() and index.column() == INTENSITY:
            autorangeAction = QAction(self.tr('Auto-Define Range'), self)
            menu = QMenu(table)
            menu.addAction(autorangeAction)
            action = menu.exec_(table.mapToGlobal(point))
            if action == autorangeAction:
                auto_list = self.auto_range()
                if auto_list:
                    model.setData(index, ','.join(auto_list), Qt.EditRole)

    @Slot(bool)
    def auto_range(self):
        dialog = ScenarioRange(self)
        dialog.setWindowModality(Qt.WindowModal)
        if dialog.exec_():
            if dialog.points:
                return dialog.points

    @Slot()
    def updateScenariosList(self):
        mat_bgnd_strings = []
        for i, model in enumerate([self.modelMat, self.modelBgnd]):
            mat_bgnd_strings.append('')
            for row in range(model.rowCount()):
                untStr = model.data(model.index(row, UNITS))
                matStr = model.data(model.index(row, MATERIAL))
                intStr = model.modelData(model.index(row, INTENSITY))
                if untStr != '' and matStr != '' and intStr != '':
                    if len(mat_bgnd_strings[i]) > 0:
                        mat_bgnd_strings[i] += '\n'
                    mat_bgnd_strings[i] += '{}({})'.format(matStr, ', '.join('{:.5f}'.format(
                        float(dose)) for dose in self.model.getSet(intStr)) + self.tr(', Units: ') + untStr)
        self.txtScenariosList_2.setText(self.tr('Source materials:\n'
                         '{}\n\nBackground materials:\n{}').format(mat_bgnd_strings[0], mat_bgnd_strings[1]))

    @Slot(bool)
    def on_btnGroups_clicked(self, checked):
        dialog = GroupSettings(self, groups=self.model.groups)
        dialog.setWindowModality(Qt.WindowModal)
        if dialog.exec_():
            self.model.setGroupsFromNames(dialog.n_groups)

    @Slot()
    def accept(self):
        self.handleEditingFinished()

        error_message, add_message = self.model.accept()
        if error_message:
            QMessageBox.critical(self, self.tr('Error encountered'), error_message)
        else:
            if add_message:
                QMessageBox.information(self, self.tr('Record Exists'), add_message)
            QDialog.accept(self)


class ScenarioModel(QAbstractItemModel):
    def __init__(self, id=None, duplicate_ids=None, data_src=None, data_bgnd=None, data_infl=None,
                 *args, **kwargs):
        super(ScenarioModel, self).__init__(*args, **kwargs)
        self.id = id
        self.duplicate_ids = duplicate_ids
        self.column_dict = self.set_column_dict()
        self._data = self.reset_data()
        self.set_scenario_defaults()
        check_groups()
        self.groups = self.setGroupsFromId()

        self.modelSource = SourceTableModel(data=data_src, id=id, duplicate_ids=duplicate_ids)
        self.modelBackground = BgndTableModel(data=data_bgnd, id=id, duplicate_ids=duplicate_ids)
        self.modelInfluences = ScenInfluencesListModel(data=data_infl, id=id, duplicate_ids=duplicate_ids)

    @property
    def acq_time(self):
        return self.data(self.index(0, 0))
    @acq_time.setter
    def acq_time(self, value):
        self.setData(self.index(0, 0), value)

    @property
    def replication(self):
        return self.data(self.index(0, 1))
    @replication.setter
    def replication(self, value):
        self.setData(self.index(0, 1), value)

    @property
    def comment(self):
        return self.data(self.index(0, 2))
    @comment.setter
    def comment(self, value):
        self.setData(self.index(0, 2), value)

    def accept(self):
        session = Session()
        integrity_error = False
        duplicate = False  #TODO: is this vestigial?
        error_message = None
        add_message = None

        if self.replication is None or self.acq_time == []:
            error_message = self.tr('No specified acquisition time or '
                                                 'number of replications. No scenarios created.')
            return error_message, add_message
        # if this is edit rather than create, need to treat differently:
        if self.id and not self.duplicate_ids:
            # check if the scenario has been changed by the user. Note that this approach
            # considers a change even if the user rewrites the previous entry identically
            self.scenario_delete()

        materials_doses = [[], []]
        for i, matsT in enumerate([self.modelSource, self.modelBackground]):
            for row in range(matsT.rowCount()):
                matName = matsT.data(matsT.index(row, MATERIAL))
                if matName and (matsT.data(matsT.index(row, INTENSITY)) or matsT.data(matsT.index(row, INTENSITY_NEUTRON))):  # skip if no intensity specified
                    matArr = []
                    for dose in self.getSet(matsT.modelData(matsT.index(row, INTENSITY))):
                        for ndose in self.getSet(matsT.modelData(matsT.index(row, INTENSITY_NEUTRON))):
                            mat = session.query(Material).filter_by(name=matName).first()
                            fd_mat = matsT.modelData(matsT.index(row, UNITS))
                            ndoseval = ndose if ndose != '' else '0'
                            matArr.append((fd_mat, mat, dose, ndoseval))
                    materials_doses[i].append(matArr)

        # cartesian product to break out scenarios from scenario group
        for acqTime in self.getSet(self.acq_time):
            if integrity_error or duplicate:
                break
            mm = product(*materials_doses[0])
            bb = product(*materials_doses[1])
            for mat_dose_arr, bckg_mat_dose_arr in product(mm, bb):
                scenMaterials = [ScenarioMaterial(
                    material=m, dose=float(d), fd_mode=u, neutron_dose=n) for u, m, d, n in mat_dose_arr]
                bcgkScenMaterials = [ScenarioBackgroundMaterial(
                    material=m, dose=float(d), fd_mode=u, neutron_dose=n) for u, m, d, n in bckg_mat_dose_arr]
                scen_groups = []
                try:
                    for groupname in self.groups:
                        scen_groups.append(
                            session.query(ScenarioGroup).filter_by(name=groupname).first())
                    if not scen_groups:
                        scen_groups.append(session.query(ScenarioGroup).filter_by(name='default_group').first())
                    # if just changing groups, add to new group without creating a new scenario
                    # creating duplicate scenarios cause no conflicts with database anymore.
                    # They simply overwrite the old scenario by doing an "OR" operation with
                    # the scenario groups
                    scen_hash = Scenario.scenario_hash(float(acqTime), scenMaterials,
                                       bcgkScenMaterials, self.modelInfluences.selected_influences)
                    scen_exists = session.query(Scenario).filter_by(id=scen_hash).first()
                    add_groups = False
                    if scen_exists:
                        for group in scen_groups:
                            if group not in scen_exists.scenario_groups:
                                add_groups = True
                                break
                        all_groups = set(g.name for g in scen_exists.scenario_groups + scen_groups)
                        if add_groups:
                            self.add_groups_to_scen(scen_exists, all_groups)
                            add_message = self.tr('At least one '
                                                   'defined scenario is already in the database; '
                                                   'adding scenario to additional groups.')
                    else:
                        session.add(Scenario(float(acqTime), self.replication, scenMaterials,
                                 bcgkScenMaterials, list(self.modelInfluences.selected_influences),
                                 scen_groups, self.comment))
                except AttributeError:
                    error_message = self.rollback_database(materials_doses, True)
                except (IntegrityError, FlushError):
                    error_message = self.rollback_database(materials_doses)
                    integrity_error = True
                    break
        # if inputting a single scenario that already exists
        if not integrity_error:
            if duplicate:
                error_message = self.rollback_database(materials_doses)
            else:
                try:
                    session.commit()
                    return error_message, add_message
                except (IntegrityError, FlushError):
                    error_message = self.rollback_database(materials_doses)
        return error_message, add_message

    def rollback_database(self, material_doses, attrib_error=False):
        session = Session()
        session.rollback()
        if attrib_error:
            error_message = self.tr('Specified something that does not exist (for example, a material that is not in '
                                             'the database). Please examine your inputs.')
        elif (material_doses[0] and len(list(product(*material_doses[0]))[0]) > 1) or \
                (material_doses[1] and len(list(product(*material_doses[1]))[0]) > 1):
            error_message = self.tr('At least one defined scenario is already in the database! Please change scenarios.')
        else:
            error_message = self.tr('This scenario is already in the database! Please change scenario.')
        return error_message

    def scenario_delete(self):
        """
        Clear existing scenario before adding the modified version
        """
        session = Session()
        scenDelete = session.query(Scenario).filter(Scenario.id == self.id)
        matDelete = session.query(ScenarioMaterial).filter(ScenarioMaterial.scenario_id == self.id)
        bckgMatDelete = session.query(ScenarioBackgroundMaterial).filter(
            ScenarioBackgroundMaterial.scenario_id == self.id)
        scenTableAssocDelete = scenDelete.first()
        scenTableAssocDelete.scenario_groups.clear()
        scenTableAssocDelete.influences.clear()
        matDelete.delete()
        bckgMatDelete.delete()
        scenDelete.delete()

    def getSet(self, data):
        values = []
        if not data:
            return [0]
        groups = data.split(',')
        for group in groups:
            group = group.strip()
            if '-' in group and ':' in group:
                start, stop, step = [float(x) for x in re.match(r'([^-]+)-([^:]+):(.*)', group).groups()]
                if step == 0:
                    values.append(start)
                    values.append(stop)
                else:
                    while start <= stop:
                        values.append(start)
                        start += step
            else:
                values.append(group)
        return values

    def add_groups_to_scen(self, scen, all_groups):
        """
        Clear groups associated with a scenario and append new ones
        """
        session = Session()
        scen.scenario_groups.clear()
        for groupname in all_groups:
            scen.scenario_groups.append(session.query(ScenarioGroup).filter_by(name=groupname).first())

    def reset_data(self):
        df = pd.DataFrame(columns=self.column_dict.keys())
        df.loc[0] = ''
        return df

    def rowCount(self, index=None):
        return 1  # Single row for the class instance

    def columnCount(self, index=None):
        # Assuming the class variables define the columns
        return len(self._data.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        # Assuming the class variables define the columns
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._data.iloc[index.row(), index.column()])

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.update_scenario()
            return True
        else:
            return False

    def setGroupsFromId(self):
        session = Session()
        if self.duplicate_ids and isinstance(self.duplicate_ids, list):
            scens = [session.query(Scenario).filter_by(id=scen).first() for scen in self.duplicate_ids]
            grps = set()
            for scen in scens:
                grps.update([grp.name for grp in scen.scenario_groups])
            return grps
        if self.id:
            scen_edit = session.query(Scenario).filter_by(id=self.id).first()
            return [grp.name for grp in scen_edit.scenario_groups]
        return []

    def setGroupsFromNames(self, names=None):
        """
        Assign scenario groups based on a list if group names
        @param names: list
        @return:
        """
        session = Session()
        self.groups = []
        if names and isinstance(names, list):
            for name in names:
                if session.query(ScenarioGroup).filter_by(name=name).first():
                    self.groups.append(name)

    def set_attributes(self, attributes: dict):
        """
        A utility function for setting several values at once. Necessary for intermediate
        validator conditions, because setData isn't automatically called in those cases
        @param attributes:
        @return:
        """
        for key, value in attributes.items():
            self._data[key][0] = str(value)

    def index(self, row, column, parent=QModelIndex()):
        if not parent.isValid() and row == 0:
            # The parent is the root item (single row for the SQLAlchemy instance)
            parentItem = self._data
        else:
            return QModelIndex()
        if column < len(parentItem.columns):
            return self.createIndex(row, column, parentItem)
        return QModelIndex()

    def parent(self, index):
        return QModelIndex()  # Flat structure, no parent

    def set_column_dict(self):
        col_list = ['acq_time', 'replication', 'comment']
        return dict(zip(col_list, range(len(col_list))))

    def set_scenario_defaults(self):
        session = Session()
        acqtime = '30'
        repl = '100'
        comment = ''
        if self.duplicate_ids and isinstance(self.duplicate_ids, list):
            repl_list = []
            acqtime_list = []
            comment_list = []
            for duplicate_id in self.duplicate_ids:
                scen = session.query(Scenario).filter_by(id=duplicate_id).first()
                if scen:
                    repl_list.append(scen.replication)
                    if str(scen.acq_time) not in acqtime_list:
                        acqtime_list.append(str(scen.acq_time))
                    if str(scen.comment) not in comment_list and str(scen.comment) != '':
                        comment_list.append(str(scen.comment))
                repl = str(max(repl_list))
                acqtime = ','.join(acqtime_list) if len(acqtime_list) > 1 else acqtime_list[0]
                if len(comment_list) == 0:
                    comment_list = ['']
                comment = ', '.join(comment_list) if len(comment_list) > 1 else comment_list[0]
        elif self.id and type(self.id) == str:
            scen = session.query(Scenario).filter_by(id=self.id).first()
            if scen:
                repl = scen.replication
                acqtime = scen.acq_time
                comment = scen.comment
        self._data.acq_time = acqtime
        self._data.replication = repl
        self._data.comment = str(comment)
        self.update_scenario()

    def update_scenario(self):
        self.dataChanged.emit(self.index(0, 0), self.index(0, self.columnCount() - 1))


class SourceTableModel(QAbstractTableModel):
    def __init__(self, data=None, id=None, duplicate_ids=None, detector_selection='all detectors',
                 *args, **kwargs):
        """
        @param data: numpy array or list of lists
        @param id: string or None
        @param duplicate_ids: list of strings (ids)
        @param args:
        @param kwargs:
        """
        super(SourceTableModel, self).__init__(*args, **kwargs)
        self._colheaders = [self.tr('Flux/Dose'), self.tr('Source Materials'), self.tr('Intensity'),
                            self.tr('Neutron Intensity (n/(cm\u00B2s))')]
        self._data = self._set_empty_data()
        if data is not None:
            self.setDataFromTable(data)
        elif duplicate_ids and isinstance(duplicate_ids, list):
            self.setDataFromDuplicates(duplicate_ids, attribute='scen_materials')
        elif id:
            self.setDataFromId(id=id, attribute='scen_materials')
        self.detector_selection = detector_selection
        self.intrinsic_specs = {}

    def assign_data(self, scenmat):
        self.layoutAboutToBeChanged.emit()
        row = (self._data == '').all(axis=1).idxmax()
        self.setData(self.index(row, UNITS), scenmat.fd_mode)
        self.setData(self.index(row, MATERIAL), scenmat.material_name)
        self.setData(self.index(row, INTENSITY), str(scenmat.dose))
        self.setData(self.index(row, INTENSITY_NEUTRON), str(scenmat.neutron_dose))
        self.layoutChanged.emit()

    def _set_empty_data(self):
        df = pd.DataFrame(np.empty((10, 4), dtype=str), columns=self._colheaders)
        return df

    def setDataFromId(self, id=None, attribute=''):
        session = Session()
        scen = session.query(Scenario).filter_by(id=id).first()
        if scen:
            self.layoutAboutToBeChanged.emit()
            for scenmat in getattr(scen, attribute):
                row = (self._data == '').all(axis=1).idxmax()
                self.setData(self.index(row, UNITS), scenmat.fd_mode)
                self.setData(self.index(row, MATERIAL), scenmat.material_name)
                self.setData(self.index(row, INTENSITY), str(scenmat.dose))
                self.setData(self.index(row, INTENSITY_NEUTRON), str(scenmat.neutron_dose))
            self.layoutChanged.emit()

    def setDataFromDuplicates(self, duplicate_ids, attribute=''):
        #handles create new scenario from existing
        session = Session()
        duplications = {}
        for id in duplicate_ids:
            scen = session.query(Scenario).filter_by(id=id).first()
            if scen:
                for scenmat in getattr(scen, attribute):
                    if scenmat.material_name not in duplications.keys():
                        duplications[scenmat.material_name] = {}
                    if scenmat.fd_mode not in duplications[scenmat.material_name].keys():
                        duplications[scenmat.material_name][scenmat.fd_mode] = []
                    if str(scenmat.dose) not in duplications[scenmat.material_name][scenmat.fd_mode]:
                        duplications[scenmat.material_name][scenmat.fd_mode].append((str(scenmat.dose), str(scenmat.neutron_dose)))
        for material, matdict in duplications.items():
            for units, doses in matdict.items():
                row = (self._data == '').all(axis=1).idxmax()
                self.setData(self.index(row, UNITS), units)
                self.setData(self.index(row, MATERIAL), material)
                self.setData(self.index(row, INTENSITY), ','.join(d[0] for d in doses))
                self.setData(self.index(row, INTENSITY_NEUTRON), ','.join(d[1] for d in doses))

    def setDataFromTable(self, data):
        """
        Takes as input anything of the form 'list of lists'. Each list element must have 3 or 4
        elements, otherwise it will be ignored
        """
        for idx, element in enumerate(data):
            if len(element) not in (3,4):
                print(self.tr('Index {} failed due to not having 3 or 4 elements.').format(idx))
                continue
            if element[0] == '':
                continue
            if element[0] not in units_labels.keys():
                print(self.tr('Index {} failed due to the first element not being the correct units').format(idx))
                continue
            self.setData(self.index(idx, UNITS), element[0])
            self.setData(self.index(idx, MATERIAL), element[1])
            self.setData(self.index(idx, INTENSITY), element[2])
            if len(element) == 4:
                self.setData(self.index(idx, INTENSITY_NEUTRON), element[3])
            else:
                self.setData(self.index(idx, INTENSITY_NEUTRON), 0)

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        col = index.column()
        if col == INTENSITY and role == Qt.ToolTipRole:
            return self.tr('Enter comma-separated values OR range as '
                                        'min-max:step OR range followed by comma-separated values')
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == UNITS:
                if self._data.iloc[row, col] == '':
                    return self._data.iloc[row, col]
                return units_labels[self._data.iloc[row, col]]
            elif col == INTENSITY and self._data.iloc[row, col] in self.intrinsic_specs.keys():
                return self.intrinsic_specs[self._data.iloc[row, col]]
            return self._data.iloc[row, col]

    @property
    def model_data(self):
        return self._data

    def modelData(self, index=None, role=Qt.DisplayRole):
        if index is None:
            return self._data
        if index.column() == MATERIAL:
            return self.data(index, role)
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._data.iloc[index.row(), index.column()])

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            if index.column() == UNITS:
                self._data.iloc[index.row(), index.column()] = ''
                for key, val in units_labels.items():
                    if value == val or value == key:
                        self._data.iloc[index.row(), index.column()] = key
            else:
                self._data.iloc[index.row(), index.column()] = value
            if index.column() not in (INTENSITY,INTENSITY_NEUTRON):
                self.on_CellChange(index)
            self.update_scenario()
            return True
        if role == Qt.CheckStateRole and index.column() not in (INTENSITY,INTENSITY_NEUTRON):
            if index.column() == UNITS:
                for key, val in units_labels.items():
                    if value == val or value == key:
                        self._data.iloc[index.row(), index.column()] = key
            else:
                self._data.iloc[index.row(), index.column()] = value
            self.on_CellChange(index)
            self.update_scenario()
            return True
        else:
            return False

    def setDataFromComboBox(self, index, editor: QComboBox):
        self.intrinsic_specs[editor.currentData(Qt.UserRole)] = editor.currentText()
        self.setData(index, editor.currentData(Qt.UserRole))

    def rowCount(self, index=None):
        return self._data.shape[0]

    def columnCount(self, index=None):
        return self._data.shape[1]

    def index(self, row, column, parent=QModelIndex()):
        if not parent.isValid():
            # The parent is the root item (single row for the SQLAlchemy instance)
            parentItem = self._data
        else:
            return QModelIndex()
        if column < len(parentItem.columns):
            return self.createIndex(row, column, parentItem)
        return QModelIndex()

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
        if index.column() == 2:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def on_CellChange(self, index):
        """
        Listens for Material table cell changed
        """
        if index.column() == UNITS:
            if self._data.iloc[index.row(), MATERIAL] and self._data.iloc[index.row(), INTENSITY]:
                if not self._data.iloc[index.row(), UNITS]:
                    self.setData(self.index(index.row(), MATERIAL), '', Qt.EditRole)
                    self.setData(self.index(index.row(), INTENSITY), '', Qt.EditRole)
                elif self._data.iloc[index.row(), MATERIAL]:
                    self.set_otherCols_fromUnit(index)
        if index.column() == MATERIAL:
            self.set_otherCols_fromMat(index)

    def set_otherCols_fromUnit(self, index):
        units = self._data.iloc[index.row(), UNITS]
        matName = self._data.iloc[index.row(), MATERIAL]
        textKeep = False
        if self.detector_selection == 'all detectors':
            detector_list = [detector for detector in Session().query(Detector)]
        else:
            detector_list = [Session().query(Detector).filter_by(name=self.detector_selection).first()]
        for detector in detector_list:
            for baseSpectrum in detector.base_spectra:
                if baseSpectrum.material.name == matName and not textKeep:
                    if (units == 'DOSE' and isinstance(baseSpectrum.rase_sensitivity, float)) or \
                       (units == 'FLUX' and isinstance(baseSpectrum.flux_sensitivity, float)):
                        textKeep = True
        if not textKeep:
            self.setData(self.index(index.row(), MATERIAL), '', Qt.EditRole)

    def set_otherCols_fromMat(self, index):
        units = self._data.iloc[index.row(), UNITS]
        matName = self._data.iloc[index.row(), MATERIAL]
        doseItem = self._data.iloc[index.row(), INTENSITY]
        if matName:
            # set default value for intensity
            if not doseItem:
                self.setData(self.index(index.row(), INTENSITY), '0.1', Qt.EditRole)
            if Session().get(Material, matName).include_intrinsic:
                self.setData(self.index(index.row(), INTENSITY), '', Qt.EditRole)
            # force units to match what is available in the selected base spectrum
            if not units:
                textSet = False
                if self.detector_selection == 'all detectors':
                    detector_list = [detector for detector in Session().query(Detector)]
                else:
                    detector_list = [Session().query(Detector).filter_by(name=self.detector_selection).first()]
                for detector in detector_list:
                    for baseSpectrum in detector.base_spectra:
                        if baseSpectrum.material.name == matName and not textSet:
                            self.setData(self.index(index.row(), UNITS), 'DOSE', Qt.EditRole) if \
                                isinstance(baseSpectrum.rase_sensitivity, float) else \
                                self.setData(self.index(index.row(), UNITS), 'FLUX', Qt.EditRole)

    def reset_data(self):
        reset_data = self._set_empty_data()
        self.setDataFromTable(reset_data)
        self.update_scenario()


    def update_scenario(self):
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount(), self.columnCount() - 1))

    def any_neutrons_in_table(self):
        return not self._data.iloc[:,INTENSITY_NEUTRON].isin(['0.0','']).all()

class BgndTableModel(SourceTableModel):
    def __init__(self, data=None, id=None, duplicate_ids=None, *args, **kwargs):
        """
        @param data: numpy array or list of lists
        @param args:
        @param kwargs:
        """
        super(BgndTableModel, self).__init__(*args, **kwargs)
        self._colheaders = [self.tr('Flux/Dose'), self.tr('Background Materials'), self.tr('Intensity'),
                            self.tr('Neutron Bgnd Scaling Factor')]
        self._data = self._set_empty_data()
        if data is not None:
            self.setDataFromTable(data)
        elif duplicate_ids and isinstance(duplicate_ids, list):
            self.setDataFromDuplicates(duplicate_ids, attribute='scen_bckg_materials')
        elif id:
            self.setDataFromId(id=id, attribute='scen_bckg_materials')
        self.detector_selection = 'all detectors'


class ScenInfluencesListModel(QAbstractListModel):
    def __init__(self, data=None, id=None, duplicate_ids=None, *args, **kwargs):
        """
        @param data: a list of influence names (list of str)
        @param id: A single ID (str)
        @param duplicate_ids: List of IDs (str)
        @param args:
        @param kwargs:
        """
        super(ScenInfluencesListModel, self).__init__(*args, **kwargs)
        self.influences = None  # a list of all the influence names in the database
        self.set_influences()
        self.selected_influences = set()
        if data is not None:
            try:
                self.setSelectedInfluences([self.influences.index(name)[0] for name in data])
            except:
                raise Exception(self.tr('Exception: Named influences do not exist in database'))
        elif duplicate_ids and isinstance(duplicate_ids, list):
            self.setDataFromDuplicates(duplicate_ids)
        elif id:
            self.setDataFromId(id)

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self.influences.clear()
        self.layoutChanged.emit()

    def index(self, row, column, parent=QModelIndex()):
        if not parent.isValid():
            # The parent is the root item (single row for the SQLAlchemy instance)
            parentItem = self.influences
        else:
            return QModelIndex()
        if row < len(parentItem):
            return self.createIndex(row, column, parentItem)
        return QModelIndex()

    def setDataFromId(self, id=None):
        session = Session()
        scen = session.query(Scenario).filter_by(id=id).first()
        if scen:
            self.layoutAboutToBeChanged.emit()
            infl_indicies = []
            for infl in scen.influences:
                try:
                    infl_indicies.append(self.influences.index(infl.name))
                except:
                    # if we are importing a scenario which has an influence that doesn't exist in this database
                    continue
            self.setSelectedInfluences(infl_indicies)
            self.layoutChanged.emit()

    def setDataFromDuplicates(self, duplicate_ids=None):  # TODO: refactor with above
        session = Session()
        self.layoutAboutToBeChanged.emit()
        infl_indicies = []
        for id in duplicate_ids:
            scen = session.query(Scenario).filter_by(id=id).first()
            if scen:
                for infl in scen.influences:
                    try:
                        if self.influences.index(infl.name) not in infl_indicies:
                            infl_indicies.append(self.influences.index(infl.name))
                    except:
                        # if we are importing a scenario which has an influence that doesn't exist in this database
                        continue
        self.setSelectedInfluences(infl_indicies)
        self.layoutChanged.emit()

    def setSelectedInfluences(self, infl_indicies=None):
        if infl_indicies is None:
            self.selected_influences = set()
        else:
            session = Session()
            self.selected_influences = set(session.query(Influence).filter_by(
                name=self.influences[idx]).first() for idx in infl_indicies)

    def set_influences(self):
        self.layoutAboutToBeChanged.emit()
        session = Session()
        influences = session.query(Influence).all()
        self.influences = sorted([influence.name for influence in influences])
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

    def rowCount(self, index):
        return len(self.influences)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.influences[index.row()]


class MaterialDoseDelegate(QItemDelegate):
    def __init__(self, parent, materialCol, intensityCol=-1, unitsCol=2, neutronCol=3, selected_detname=None,
                 editable=False, auto_s=False, tables=None):
        super(MaterialDoseDelegate, self).__init__(parent)
        self.tblMat = parent
        self.tables = tables
        self.matCol = materialCol
        self.intensityCol = intensityCol
        self.unitsCol = unitsCol
        self.neutronCol = neutronCol
        self.editable = editable
        self.selected_detname = selected_detname
        self.auto_s = auto_s
        self.settings = RaseSettings()

    def createEditor(self, parent, option, index):
        if index.column() == self.matCol:
            # generate material list
            fd_units = ''
            for key, val in units_labels.items():
                if self.tblMat.data(self.tblMat.index(index.row(), UNITS)) == val:
                    fd_units = key
                    break
            material_list = []
            if not self.selected_detname:
                for detector in Session().query(Detector):
                    for baseSpectrum in detector.base_spectra:
                        if baseSpectrum.material.name not in material_list:
                            if ((isinstance(baseSpectrum.rase_sensitivity, float) and (fd_units == 'DOSE')) or
                                (isinstance(baseSpectrum.flux_sensitivity, float) and (fd_units == 'FLUX')) or
                                    not fd_units):
                                material_list.append(baseSpectrum.material.name)
                material_list = sorted(material_list)
            else:
                detector = Session().query(Detector).filter_by(name=self.selected_detname).first()
                material_list = sorted([baseSpectrum.material.name for baseSpectrum in detector.base_spectra if
                                        ((isinstance(baseSpectrum.rase_sensitivity, float) and (fd_units == 'DOSE')) or
                                         (isinstance(baseSpectrum.flux_sensitivity, float) and (fd_units == 'FLUX')) or
                                            not fd_units)])

            intrinsic_material_present = False
            for table in self.tables:
                for row in range(table.rowCount()):
                    if row == index.row() and table is self.tblMat:
                        continue
                    item = table.data(table.index(row, self.matCol))
                    # remove any materials already used
                    if item in material_list:
                        material_list.remove(item)
                    # check if at least one material include intrinsic source
                    if item and Session().get(Material, item).include_intrinsic:
                        intrinsic_material_present = True
            if intrinsic_material_present:  # only one material with intrinsic source is allowed
                for material in material_list:
                    if Session().get(Material, material).include_intrinsic:
                        material_list.remove(material)

            #create and populate comboEdit
            comboEdit = QComboBox(parent)
            comboEdit.setEditable(self.editable)
            comboEdit.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            comboEdit.setMaxVisibleItems(25)
            comboEdit.addItem('')
            comboEdit.addItems(material_list)
            return comboEdit
        elif index.column() in [self.intensityCol, self.neutronCol]:
            return self.intensityEditor(parent, index)
        elif index.column() == self.unitsCol:
            return self.comboEditor(parent, index, units_labels)
        else:
            return super(MaterialDoseDelegate, self).createEditor(parent, option, index)

    def intensityEditor(self, parent, index):
        mat_name = self.tblMat.data(self.tblMat.index(index.row(), self.matCol), Qt.DisplayRole)
        if mat_name and Session().get(Material, mat_name).include_intrinsic:
            fd_units = ''
            for key, val in units_labels.items():
                if self.tblMat.data(self.tblMat.index(index.row(), UNITS)) == val:
                    fd_units = key
                    break
            intensity_labels = {}
            for base_spectrum in Session().query(BaseSpectrum).filter_by(material_name=mat_name):
                if self.selected_detname and base_spectrum.detector_name != self.selected_detname:
                    continue
                if isinstance(base_spectrum.rase_sensitivity, float) and (fd_units == 'DOSE'):
                    intensity_value = str(base_spectrum.get_measured_dose_and_flux()[0])
                elif isinstance(base_spectrum.flux_sensitivity, float) and (fd_units == 'FLUX'):
                    intensity_value = str(base_spectrum.get_measured_dose_and_flux()[1])
                else:
                    continue
                if intensity_value in intensity_labels:
                    intensity_desc = intensity_labels[intensity_value].replace('Instrument', 'Instruments')
                    intensity_desc += f', {base_spectrum.detector_name}'
                else:
                    intensity_desc = f'{intensity_value} - Instrument: {base_spectrum.detector_name}'
                intensity_labels[intensity_value] = intensity_desc
            return self.comboEditor(parent, index, intensity_labels)
        else:
            editor = QLineEdit(parent)
            editor.setValidator(RegExpSetValidator(editor, self.auto_s))
            return editor

    def setModelData(self, editor, model, index):
        if index.column() == self.unitsCol:
            self.tblMat.setData(index, editor.currentData(Qt.UserRole))
        if index.column() == self.matCol:
            self.tblMat.setData(index, editor.currentText())
        if index.column() in [self.intensityCol, self.neutronCol]:
            if type(editor) == QLineEdit:
                self.tblMat.setData(index, editor.text())
            elif type(editor) == QComboBox:
                self.tblMat.setDataFromComboBox(index, editor)

    def comboEditor(self, parent, index, map):
        self.tblMat.setData(index, '', Qt.UserRole)
        model = QStandardItemModel(0, 1)
        for key, text in map.items():
            item = QStandardItem(text)
            item.setData(key, Qt.UserRole)
            model.appendRow(item)
        comboEdit = QComboBox(parent)
        comboEdit.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        comboEdit.setModel(model)
        comboEdit.setCurrentIndex(comboEdit.findData(self.tblMat.data(index)))
        return comboEdit


class ScenarioRange(ui_scenario_range_dialog.Ui_RangeDefinition, QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.points = []
        self.help_dialog = None
        self.setupUi(self)

        self.line_max.setValidator(DoubleValidator(self.line_max))
        self.line_max.validator().setBottom(0.)
        self.line_max.validator().validationChanged.connect(self.handle_validation_change)

        self.line_min.setValidator(DoubleValidator(self.line_min))
        self.line_min.validator().setBottom(0.)
        self.line_min.validator().validationChanged.connect(self.handle_validation_change)
        self.line_min.textEdited.connect(self.update_max_validator_range)

        self.line_num.setValidator(IntValidator(self.line_num))
        self.line_num.validator().setBottom(1)
        self.line_num.validator().validationChanged.connect(self.handle_validation_change)

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.line_dose.setValidator(DoubleValidator(self.line_dose))
        self.line_dose.validator().setBottom(1e-6)
        self.line_dose.validator().validationChanged.connect(self.handle_validation_change)

        self.line_distance.setValidator(DoubleValidator(self.line_distance))
        self.line_distance.validator().setBottom(1)
        self.line_distance.validator().validationChanged.connect(self.handle_validation_change)

        for widget in [self.line_num, self.line_max, self.line_min, self.line_dose, self.line_distance]:
            widget.textEdited.connect(self.update_calc)
        for widget in [self.radio_distance, self.radio_dose, self.radio_lin, self.radio_log]:
            widget.clicked.connect(self.update_calc)

        self.on_radio_distance_toggled(False)

        self.btnInfo.clicked.connect(self.open_help)

    @Slot(bool)
    def on_radio_distance_toggled(self, checked):
        self.wdgtDistanceParams.setVisible(checked)
        tmp_str = 'distance' if checked else 'dose/flux'
        self.label_minimum.setText(self.tr('Minimum {}:').format(tmp_str))
        self.label_maximum.setText(self.tr('Maximum {}:').format(tmp_str))

    @Slot(QValidator.State)
    def handle_validation_change(self, state):
        if state == QValidator.Invalid:
            color = 'red'
        elif state == QValidator.Intermediate:
            color = 'gold'
        elif state == QValidator.Acceptable:
            color = 'green'
        sender = self.sender().parent()
        sender.setStyleSheet(f'border: 2px solid {color}')
        # QtCore.QTimer.singleShot(1000, lambda: sender.setStyleSheet(''))

    @Slot(str)
    def update_max_validator_range(self, text):
        if self.sender().hasAcceptableInput():
            self.line_max.validator().setBottom(float(text) if text else 0.)

    @Slot(str)
    @Slot(bool)
    def update_calc(self, dummy):
        """Update computed points if all the relevant input are correct"""
        state = self.line_min.hasAcceptableInput() and self.line_max.hasAcceptableInput() \
                and self.line_num.hasAcceptableInput()
        if self.radio_distance.isChecked():
            state = state and self.line_dose.hasAcceptableInput() and self.line_distance.hasAcceptableInput()
        if state:
            self.calculate_range()
            self.display_points()
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def calculate_range(self):
        range_min = float(self.line_min.text())
        range_min = 1.0e-12 if range_min == 0 else range_min
        range_max = float(self.line_max.text())
        steps = int(self.line_num.text())

        if self.radio_lin.isChecked():
            points = np.linspace(range_min, range_max, steps)
        else:
            points = np.geomspace(range_min, range_max, steps)

        if self.radio_distance.isChecked():
            ref_distance = float(self.line_distance.text())
            ref_dose = float(self.line_dose.text())
            points = ref_dose * np.power(ref_distance / points, 2)

        self.points = [f'{point:g}' for point in points]

    def display_points(self):
        """Display computed points"""
        model = QStandardItemModel()
        self.listView.setModel(model)
        for i in self.points:
            item = QStandardItem(i)
            item.setEditable(False)
            model.appendRow(item)

    def open_help(self):
        if not self.help_dialog:
            self.help_dialog = HelpDialog(page='Use_distance.html')
        if self.help_dialog.isHidden():
            self.help_dialog.load_page(page='Use_distance.html')
            self.help_dialog.show()
        self.help_dialog.activateWindow()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    from src.rase import Rase
    from src.rase_functions import delete_scenario
    from src.rase_settings import RaseSettings
    import sys

    app = QApplication(sys.argv)  # required to call RASE object
    r = Rase(args='')
    settings = RaseSettings()
    foo = ScenarioModel(data_src=np.array([['FLUX', 'Cs137', '0.10101']]),
                        data_bgnd=np.array([['DOSE', 'Bgnd', '0.0101']]))
    foo.comment = 'TestComment'
    foo.accept()

    session = Session()
    scen = session.query(Scenario).filter_by(comment='TestComment').first()
    assert scen is not None
    delete_scenario([scen.id], settings.getSampleDirectory())
    scen = session.query(Scenario).filter_by(comment='TestComment').first()
    assert scen is None


