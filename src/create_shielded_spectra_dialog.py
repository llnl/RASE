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
"""
This module handles shielded spectra creation
"""
import logging
import os, sys
import yaml
from PySide6.QtCore import Qt, Slot, QAbstractItemModel, QAbstractListModel, QModelIndex
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QDialog, QFileDialog, QDataWidgetMapper

from src.qt_utils import BaseSpectraListModel, Translatable
from src.rase_functions import get_or_create_material
from src.rebin import rebin
from src.rase_settings import RaseSettings
from src.table_def import BaseSpectrum, Detector, Session

from src.ui_generated import ui_create_shielded_spectra_dialog
import pandas as pd
import numpy as np


class CreateShieldedSpectraDialog(ui_create_shielded_spectra_dialog.Ui_CreateShieldedBaseSpectraDialog, QDialog):
    def __init__(self, parent, detectorName=None,shield_drf=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setupUi(self)
        self.add_detectors()
        self.model = ShieldingModel(detectorName)
        self.modelBSL = self.model.modelBSL
        self.modelThick = self.model.modelThick
        self.modelOut = self.model.modelOut
        self.assign_listviews()
        self.lstBaseSpectra.setModel(self.modelBSL)
        self.lstThickness.setModel(self.modelThick)
        self.lstOutSpecs.setModel(self.modelOut)
        self.model_comboboxes = [self.cmbDetectors, self.cmbDrf, self.cmbShield]
        self.model_lineedits = [self.txtConfigPath, self.txtChNum, self.txtEcal0, self.txtEcal1,
                                                                    self.txtEcal2, self.txtEcal3]

        self.cmbDetectors.currentTextChanged.connect(self.model.setDataFromDetector)
        self.cmbDetectors.currentTextChanged.connect(self.add_drf_items)
        self.cmbDetectors.currentTextChanged.connect(lambda: self.lstBaseSpectra.clearSelection())

        self.cmbDrf.currentTextChanged.connect(lambda: self.model.setData(self.model.column_dict['drf'],
                                                                          self.cmbDrf.currentText()))  # is there a smarter way?
        self.cmbShield.currentTextChanged.connect(lambda: self.model.setData(self.model.column_dict['shielding'],
                                                                             self.cmbShield.currentText()))  # is there a smarter way?

        self.cmbDrf.currentTextChanged.connect(self.model.set_shieldings_from_drf)
        self.cmbDrf.currentTextChanged.connect(self.add_shielding_items)
        self.cmbDrf.currentTextChanged.connect(lambda: self.lstThickness.clearSelection())
        self.cmbShield.currentTextChanged.connect(lambda: self.lstThickness.clearSelection())

        self.model.dataChanged.connect(self.model.set_thickness)
        self.modelOut.layoutChanged.connect(lambda: self.cmbDetectors.setEnabled(self.modelOut.rowCount() == 0))
        self.modelOut.layoutChanged.connect(lambda: self.cmbDrf.setEnabled(self.modelOut.rowCount() == 0))
        self.modelOut.layoutChanged.connect(lambda: self.btnExport.setEnabled(self.modelOut.rowCount() > 0))
        self.modelOut.layoutChanged.connect(lambda: self.lstOutSpecs.clearSelection())

        self.mapper_lineedit = QDataWidgetMapper()
        self.mapper_lineedit.setModel(self.model)
        self.set_modelmap(self.mapper_lineedit, self.model_lineedits, self.model.col_names_lineedit)
        self.mapper_lineedit.toFirst()
        self.mapper_comboedit = QDataWidgetMapper()
        self.mapper_comboedit.setModel(self.model)
        self.set_modelmap(self.mapper_comboedit, self.model_comboboxes, self.model.col_names_combobox)
        self.mapper_comboedit.toFirst()

        if shield_drf is not None and shield_drf in self.model.drfs:
            self.cmbDrf.setCurrentText(shield_drf)

        self.model.update_shielded_spectra()

    def set_modelmap(self, mapper, viewvals, modelvals):
        for w, c in zip(viewvals, modelvals):
            mapper.addMapping(w, self.model.column_dict[c].column())

    def assign_listviews(self):
        func = type(self).custom_mousePressEvent
        for widget in (self.lstBaseSpectra, self.lstThickness, self.lstOutSpecs):
            widget.mousePressEvent = func.__get__(widget, type(widget))

    def add_detectors(self):
        session = Session()
        self.cmbDetectors.clear()
        self.cmbDetectors.addItems([''] + [d.name for d in session.query(Detector).all() if len(d.base_spectra) > 0])
        self.cmbDetectors.setCurrentIndex(0)

    def add_drf_items(self):
        self.cmbDrf.clear()
        self.cmbDrf.addItems(self.model.drfs)
        self.cmbDrf.setCurrentText(self.model.data(self.model.column_dict['drf']))  # causes infinite loop

    def add_shielding_items(self):
        self.cmbShield.clear()
        self.cmbShield.addItems(self.model.shieldings)
        self.cmbShield.setCurrentText(self.model.data(self.model.column_dict['shielding']))  # causes infinite loop

    @Slot(bool)
    def on_btnBrowseConfig_clicked(self, checked):
        """
        Selects configuration file
        """
        if sys.platform.startswith('win'):
            options = QFileDialog.DontUseNativeDialog
        path, __filter = QFileDialog.getOpenFileName(self, self.tr('Choose Config YAML file'),
                                                     self.model.settings.getLastDirectory(), 'YAML(*.yaml)')
        if path:
            self.model.set_config_path(path)
            self.add_drf_items()            # could make list model, but not for time (and simple implementation)
            self.add_shielding_items()

    @Slot(bool)
    def on_btnAddConfig_clicked(self, checked):
        """
        Adds selected base spectra + drf + shieldings + thicknesses to the output list
        """
        bs_indices = self.lstBaseSpectra.selectedIndexes()
        base_spectra = [bs_indices[k].data() for k in range(len(bs_indices))]
        thick_indices = self.lstThickness.selectedIndexes()
        shield_thicknesses = [thick_indices[k].data() for k in range(len(thick_indices))]
        if len(base_spectra) > 0 and len(shield_thicknesses) > 0:
            self.model.add_spectra(self.model.data(self.model.column_dict['detector']),
                                    self.model.data(self.model.column_dict['drf']),
                                    self.model.data(self.model.column_dict['shielding']),
                                    base_spectra, shield_thicknesses)

    @Slot(bool)
    def on_btnRemoveConfigs_clicked(self, checked):
        """
        Adds selected base spectra + drf + shieldings + thicknesses to the output list
        """
        keys = [self.modelOut.data(k) for k in self.lstOutSpecs.selectedIndexes()]
        self.model.remove_spectra(keys)

    @Slot(bool)
    def on_btnExport_clicked(self, checked):
        """
        Opens a window where the user selects an output folder for exporting
        """
        dialog = QFileDialog(self, self.tr("Choose Export Directory"))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)  # Only show directories
        dialog.setLabelText(QFileDialog.Accept, self.tr("Export"))  # Change "Open" to "Export"
        dialog.setLabelText(QFileDialog.LookIn, self.tr("Export Directory"))

        if sys.platform.startswith('win'):
            dialog.setOption(QFileDialog.DontUseNativeDialog, True)

        dialog.setDirectory(self.model.settings.getLastDirectory())

        if dialog.exec():
            export_dir = dialog.selectedFiles()[0]  # Check only one directory will be here
            _, shielded_specs = self.model.process_shielding()
            self.model.export_spectra(shielded_specs, export_dir, self.cmbDetectors.currentText())

    def custom_mousePressEvent(self, event: QMouseEvent):
        """
        Allows user to clear all selections by clicking a dead space in list view
        """
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
        super(type(self), self).mousePressEvent(event)

    def accept(self):
        self.model.accept()
        return QDialog.accept(self)


class ShieldingModel(QAbstractItemModel):
    def __init__(self, detector_name=None, *args, **kwargs):
        super(ShieldingModel, self).__init__(*args, **kwargs)
        self.modelBSL = BaseSpectraListModel()
        self.modelThick = ShieldThicknessListModel()
        self.modelOut = OutSpecsListModel()
        self.settings = RaseSettings()
        self.col_names_combobox = ['detector', 'drf', 'shielding']
        self.col_names_lineedit = ['config_file', 'ch_num', 'ecal0', 'ecal1', 'ecal2', 'ecal3']
        self.col_names = self.col_names_combobox + self.col_names_lineedit
        self._data = self.reset_data()
        self.drfs = ['']
        self.shieldings = ['']
        self.config = self._load_configs()
        self._rolledback = False
        self.column_dict = self.set_column_dict()
        self.setDataFromDetector(detector_name)
        self.setData(self.column_dict['config_file'], self.settings.getShieldingPathConfig())

    @property
    def model_data(self):
        return self._data

    def set_column_dict(self):
        return dict(zip(self.col_names, (self.index(0, r) for r in range(len(self.col_names)))))

    def reset_data(self):
        df = pd.DataFrame(columns=self.col_names)
        df.loc[0] = ''
        return df

    def set_config_path(self, path=None):
        if path:
            self.setData(self.column_dict['config_file'], path)
            self.settings.setShieldingPathConfig(path)
        self.config = self._load_configs()

    def _load_configs(self):
        if not os.path.isfile(self.settings.getShieldingPathConfig()):
            raise Exception(self.tr('Shielding file does not exist!'))
        with open(self.settings.getShieldingPathConfig(), mode='r') as file:
            return yaml.safe_load(file)

    def set_all_from_chnum(self):
        self.set_drfs_from_chnum()
        self.set_shieldings_from_drf(self._data['drf'][0])
        self.set_thickness()

    def set_drfs_from_chnum(self):
        if self._data['ch_num'][0] not in self.config.keys():
            return
        self.drfs = list(k for k in self.config[self._data['ch_num'][0]].keys() if type(
                            self.config[self._data['ch_num'][0]][k]) == dict)
        self.setData(self.column_dict['drf'], self.drfs[0])
        self.update_shielded_spectra()

    def set_shieldings_from_drf(self, drf):
        if self._data['ch_num'][0] not in self.config.keys():
            return
        if drf in self.config[self._data['ch_num'][0]].keys():
            self.shieldings = list(k for k in self.config[self._data['ch_num'][0]][drf].keys() if type(
                            self.config[self._data['ch_num'][0]][drf][k]) == dict)
            self.setData(self.column_dict['shielding'], self.shieldings[0])
            self.update_shielded_spectra()

    def set_thickness(self):
        try:
            self.modelThick.set_thicknesses(self.config[self._data['ch_num'][0]][self._data['drf'][0]][
                                                self._data['shielding'][0]])
        except:
            self.modelThick.set_thicknesses(None)

    def setDataFromDetector(self, detector_name=''):
        session = Session()
        detector = session.query(Detector).filter_by(name=detector_name).first()
        if detector is not None:
            self.setData(self.column_dict['detector'], detector.name)
            self.setData(self.column_dict['ch_num'], detector.chan_count)
            for i in range(4):
                self.setData(self.column_dict[f'ecal{i}'], detector.__getattribute__(f'ecal{i}'))
            self.modelBSL.update_fromdetector(detector.name)
            self.set_all_from_chnum()
        self.update_shielded_spectra()

    def add_spectra(self, det_name, drf, shieldmat, base_spectra, shield_thicknesses):
        self.modelOut.add_spectra(det_name, drf, shieldmat, base_spectra, shield_thicknesses,
                                  self.config[self._data['ch_num'][0]])

    def remove_spectra(self, keys):
        self.modelOut.remove_spectra(keys)

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
            return str(self._data.iloc[0, index.column()])

    def setData(self, index, value, role=Qt.EditRole):
        if self._rolledback:
            # stop GUI from trying to modify model anymore (which can cause session crash issues)
            return False
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            self._data.iloc[0, index.column()] = value
            self.update_shielded_spectra()
            return True
        return False

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

    def parent(self, index):
        return QModelIndex()  # Flat structure, no parent

    def update_shielded_spectra(self):
        self.dataChanged.emit(self.index(0, 0), self.index(0, self.columnCount() - 1))

    def process_shielding(self):
        outlist = self.modelOut.model_data
        # TODO: account for how the ecals are actually accessed here. They're supposed to be pulled from the sub-detector field
        det_name = self.model_data['detector'][0]
        ch_num = self.model_data['ch_num'][0]
        drf = self.model_data['drf'][0]
        try:
            shieldmod = ShieldingModule(det_name=det_name, ch_num=ch_num, ecals=self.config[ch_num][drf]['ecals'],
                            inst_rootpath=self.config['inst_configs'], shield_rootpath=self.config['shield_configs'])
        except KeyError:
            return None, None
        shielded_specs = shieldmod.apply_shielding(outlist)
        return shieldmod, shielded_specs

    def export_spectra(self, spectra, outdir, detector_name):
        """
        Export to the chosen directory
        :param spectra:
        :param outdir:
        :param detector_name:
        :return:
        """
        from src.base_building_algos import build_base_ET, write_base_ET, rawvalues_from_basespec
        from lxml import etree
        session = Session()
        detector = session.query(Detector).filter_by(name=detector_name).first()

        for spectrum in spectra:
            values = rawvalues_from_basespec(spectrum)
            if detector.secondary_spectra:
                d = dict()
                for spec in detector.secondary_spectra:
                    d[spec.classcode] = spec
                values.secondaries = d
            outET = build_base_ET(rawValues=values)
            write_base_ET(etree.ElementTree(etree.fromstring(bytes(outET, encoding='utf-8'))), outdir, spectrum.filename)

    def accept(self):
        """
        Make the shielded base spectra, attach to detector
        """
        shieldmod, shielded_specs = self.process_shielding()
        if shieldmod is not None and shielded_specs is not None:
            shieldmod.add_to_detector(shielded_specs)


class ShieldThicknessListModel(QAbstractListModel):
    def __init__(self, data=None, filepath=None, *args, **kwargs):
        super(ShieldThicknessListModel, self).__init__(*args, **kwargs)
        self._data = data or []

    @property
    def model_data(self):
        return self._data

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self._data = []
        self.update_thicknesses()
        self.layoutChanged.emit()


    def set_thicknesses(self, thicknesses=None):
        self.layoutAboutToBeChanged.emit()
        if thicknesses is not None:
            self._data = thicknesses
        else:
            self.reset_data()
        self.update_thicknesses()
        self.layoutChanged.emit()

    def rowCount(self, index=None):
        return len(self._data)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return list(self._data.keys())[index.row()]

    def update_thicknesses(self):
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0))


class OutSpecsListModel(QAbstractListModel):
    def __init__(self, data=None, *args, **kwargs):
        super(OutSpecsListModel, self).__init__(*args, **kwargs)
        self._data = data or {}  # data should always be None in practice

    @property
    def model_data(self):
        return self._data

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self._data.clear()
        self.update_outconfigs()
        self.layoutChanged.emit()

    def add_spectra(self, det_name, drf, shieldmat, base_spectra, shield_thickness, config_fixedchnum):
        self.layoutAboutToBeChanged.emit()
        session = Session()
        for spectrum in base_spectra:
            for thickness in shield_thickness:
                element_key = f'{det_name}_{drf}: {spectrum}_{thickness}{shieldmat}'
                path_nullinv = config_fixedchnum[drf]['null_inv']
                path_nullshield = config_fixedchnum[drf][shieldmat][thickness]
                path_drfinv = config_fixedchnum[drf][drf + '_inv']
                path_drf = config_fixedchnum[drf][drf]
                spec = session.query(BaseSpectrum).filter_by(detector_name=det_name, material_name=spectrum).first()
                element_paths = (spec, path_nullinv, path_nullshield, path_drfinv, path_drf)
                if element_key not in self._data.keys():
                    self._data[element_key] = element_paths
        self.update_outconfigs()
        self.layoutChanged.emit()

    def remove_spectra(self, keys):
        self.layoutAboutToBeChanged.emit()
        self._data = {k:v for k, v in self._data.items() if k not in keys}
        self.update_outconfigs()
        self.layoutChanged.emit()

    def rowCount(self, index=None):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return list(self._data.keys())[index.row()]

    def update_outconfigs(self):
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0))


class ShieldingModule(Translatable):
    def __init__(self, det_name: str, ch_num: int = 1024, ecals: tuple = (0, 3, 0, 0),
                 inst_rootpath: str = '.', shield_rootpath: str = '.'):
        """
        :param det_name: str, name of the instrument we are creating spectra for
        :param ch_num: int, channel number of the detector we are working with
        :param ecals: tuple, ecal0, 1, 2, and 3 for the DRF of detector <det_name> (uses same ecal as null)
        :param inst_rootpath: str, path to the root directory containing all the instrument drf matrices
        :param shield_rootpath: str, path to the root directory containing all the null and null shield matrices
        :return:
        """
        self.det_name = det_name
        self.ch_num = ch_num
        self.ecals = ecals
        self.inst_rootpath = inst_rootpath
        self.shield_rootpath = shield_rootpath
        self.settings = RaseSettings()

    def load_matrix(self, filepath):
        """
        Load the response matrix from a .csv file (to do: make np arrays for better compression)
        """
        return np.load(filepath, allow_pickle=False)['data']
        # return np.array(pd.read_csv(filepath, header=None))

    def load_responses(self, path_nullinv, path_nullshield, path_drfinv, path_drf):
        """
        Load the response matrices and check the shapes to make sure they are compatible
        """
        try:
            nullinv = self.load_matrix(path_nullinv)
            nullshield = self.load_matrix(path_nullshield)
            drfinv = self.load_matrix(path_drfinv)
            drf = self.load_matrix(path_drf)
        except FileNotFoundError as e:
            raise FileNotFoundError(self.tr('Could not find the path to one of '
                                           'the shield matrix files. Try modifying your yaml. Error: {}').format(e))
        try:
            assert tuple(reversed(nullinv.shape)) == nullshield.shape
        except ValueError as e:
            raise ValueError(self.tr('Null matrices shapes are incompatible: '
                                             'inverse null shape = {}, null shield shape = {}. Error: {}').format(
                                            nullinv.shape, nullshield.shape, e))
        try:
            assert tuple(reversed(drfinv.shape)) == drf.shape
        except ValueError as e:
            raise ValueError(self.tr('Drf matrices shapes are incompatible: '
                                                     'inverse drf shape = {}, drf shape = {}. Error: {}').format(
                                                    drfinv.shape, drf.shape, e))
        try:
            assert drfinv.shape[0] == nullinv.shape[0]
        except ValueError as e:
            raise ValueError(self.tr('Drf and null matrix shapesare incompatible: '
                                             'inverse drf shape = {}, inverse null shape = {}.  Error: {}').format(
                                        drfinv.shape, nullinv.shape, e))
        return [nullinv, nullshield], [drfinv, drf]

    def iterative_matmul(self, input_list):
        """
        Faster solver than recursive for an arbitrary series of matrices
        """
        y = input_list[-1]
        for mat in reversed(input_list[:-1]):
            y = np.matmul(mat, y)
        return y

    def interpolate_response(self, thickness: float, matrices: dict, inv: str):
        """
        Takes a thickness value and a dictionary of matrices to interpolate between:
        :param thickness: float, thickness we want to interpolate to in units of [cm]
        :param matrices: dict with 2 entries of the form {thickness: shielding_matrix}
            - thickness is a float and is in units of [cm]
            - shielding_matrix is a path to the null numpy matrix associated with that thickness
                for the material we are looking at
            If the entry we are looking at is beyond the thickness value we have simulated, we will
            simply take the closest two thicknesses and extrapolate
        :param inv: path to the null_inv matrix
        :return:
        """
        if len(matrices) < 2:
            raise Exception(self.tr('Must supply two matrices'))

        from scipy.linalg import expm, logm

        new_matrices = {}
        inv_mat = self.load_matrix(inv)
        # make sure the LLD for both shield matrices are the same
        max_lld = 0
        for t, p in matrices.items():
            new_matrices[t] = self.get_T(inv_mat, self.load_matrix(p))
            for i in range(new_matrices[t].shape[1]):
                if sum(new_matrices[t][:,i]) != 0:
                    if i > max_lld:
                        max_lld = i
                    break
        for m in new_matrices.values():
            m[:,:max_lld] = 0

        l_0 = min(new_matrices.keys())
        l_1 = max(new_matrices.keys())

        # if requested shielding is thinner than the thinnest pre-simulated shielding matrix
        if thickness < l_0:
            # Calculate blend function to weight the closest pick point higher in a smooth fashion s
            f = thickness / l_0
            l_1 = l_0
            l_0 = 0
            new_matrices[l_0] = np.identity(inv_mat.shape[0])
            A = (1 - f) * new_matrices[l_0] + f * expm(logm(new_matrices[l_1]) * (thickness / l_1))
            return A.real
        # if requested shielding is thicker than the thickest pre-simulated shielding matrix
        if thickness > l_1:
            extrapolated_value = new_matrices[l_1].copy()
            new_matrices[l_0] = new_matrices[l_1].copy()
            l_0 = l_1
            while thickness > l_1:  # continue to apply shield layers
                l_1 += l_0
                extrapolated_value = self.iterative_matmul([extrapolated_value, new_matrices[l_0]])
            new_matrices[l_1] = extrapolated_value.copy()
        # Calculate blend function to weight the closest pick point higher in a smooth fashion
        f = (np.log(thickness) - np.log(l_0)) / (np.log(l_1) - np.log(l_0))
        if new_matrices[l_0].max() == 0 or new_matrices[l_1].max() == 0:
            return np.zeros(new_matrices[l_0].shape)
        A = expm( (1 - f) * (thickness / l_0) * logm(new_matrices[l_0]) +
                   f * (thickness / l_1) * logm(new_matrices[l_1]) )
        return A.real  # imaginary components are several orders of magnitude below real

    def get_T(self, nullinv, nullshield):
        """
        Generates the T matrix, which serves to transform the source flux through shielding
        """
        return np.matmul(nullshield.T, nullinv.T).T

    def rebin_spec_todrf(self, spec=None):
        """
        Take the original spectrum and rebin it to be compatible with the null and drf calibration (self.ecal)
        """
        counts = [float(k) for k in spec.baseCounts.split(',')]
        orig_calib_coeffs = [spec.ecal0, spec.ecal1, spec.ecal2, spec.ecal3]
        oldenergies = np.polyval(np.flip(orig_calib_coeffs), np.arange(len(counts) + 1))
        newspec = np.array(rebin(counts, oldenergies, self.ecals))
        return newspec

    def rebin_spec_tomeasured(self, counts=None, goal_ecal=(0, 3, 0, 0)):
        """
        Take the shielded spectrum and rebin it back into the original detector's calibration coefficients
        """
        oldenergies = np.polyval(np.flip(self.ecals), np.arange(len(counts) + 1))
        newspec = np.array(rebin(counts, oldenergies, goal_ecal))
        return newspec

    def build_base_spectrum(self,  shielded_counts, orig_spec, outname=''):
        """
        Add the base spectra to the database
        """
        session = Session()
        new_rase_sensitivity = orig_spec.rase_sensitivity * sum(shielded_counts) / sum(orig_spec.counts) if (
                orig_spec.rase_sensitivity is not None) else None
        new_flux_sensitivity = orig_spec.flux_sensitivity * sum(shielded_counts) / sum(orig_spec.counts) if (
                orig_spec.flux_sensitivity is not None) else None
        if outname:
            shielded_mat = get_or_create_material(session, outname.split(': ')[-1] + '*')
        else:
            shielded_mat = orig_spec.material
        base_spectrum = BaseSpectrum(orig_spec, filename=f'{outname}.n42',
                                     material=shielded_mat, material_name=shielded_mat.name,
                                     rase_sensitivity=new_rase_sensitivity, flux_sensitivity=new_flux_sensitivity,
                                     baseCounts=','.join(f'{k:.3f}' if k > 0 else '0' for k in shielded_counts))
        return base_spectrum

    def apply_shielding(self, outspecs):
        """
        The full processing
        outspecs: a list/tuple of components associated with each item in the output list. This includes:
            - The output name ({material}_{thickness}{shield})
            - The input spectrum as a Spectrum() object
            - Paths to the inverse null, shielded null, inverted drf, and normal drf for the selected options,
                pulled from the dictionary
        detector_name: the selected instrument for which the shielded spectra are being created
        """
        new_spectra = []
        #TODO: get pathing right
        for outname, (spec, path_nullinv, path_nullshield, path_drfinv, path_drf) in outspecs.items():
            null_responses, drf_responses = self.load_responses(os.path.join(self.shield_rootpath, str(self.ch_num),
                                 path_nullinv), os.path.join(self.shield_rootpath, str(self.ch_num), path_nullshield),
                                                    os.path.join(self.inst_rootpath, str(self.ch_num), path_drfinv),
                                                    os.path.join(self.inst_rootpath, str(self.ch_num), path_drf))
            outcounts = self.process_matrices(null_responses, drf_responses, spec)
            new_spectra.append(self.build_base_spectrum(outcounts, spec, outname))
        return new_spectra

    def remove_artifacts_zeroing_peakfind(self, spectrum_A, spectrum_B, window_length=11, polyorder=3, rel_thresh=0.0):
        """Conservative peak finding code that removes artifacts introduced at high energies by the shield algorithm"""
        from scipy.signal import savgol_filter, find_peaks
        # Smooth spectrum A
        # TODO: answer question "does this work for HPGes?"
        smoothed_A = savgol_filter(spectrum_A, window_length=window_length, polyorder=polyorder)

        # Find peaks in spectrum A
        min_prominence = max(10, 0.001 * np.max(smoothed_A))
        peaks, _ = find_peaks(smoothed_A, prominence=min_prominence)
        peak_heights = smoothed_A[peaks]
        threshold = rel_thresh * np.max(smoothed_A)
        significant_peaks = peaks[peak_heights > threshold]
        if len(significant_peaks) == 0:
            significant_peaks = peaks  # fallback: use all found peaks

        # Select highest-energy peak
        highest_energy_peak = significant_peaks[-1]  # peaks are in ascending channel order

        # Estimate peak width (fit a Gaussian to a window around the peak)
        peak_max = spectrum_A[highest_energy_peak]
        threshold = max(3, 0.01 * peak_max)
        cutoff_channel = highest_energy_peak
        for i in range(highest_energy_peak + 1, len(spectrum_A)):
            if spectrum_A[i] < threshold:
                cutoff_channel = i
                break
        cutoff_channel = min(cutoff_channel, len(spectrum_B) - 1)

        # Zero out spectrum B above cutoff
        cleaned_B = spectrum_B.copy()
        cleaned_B[cutoff_channel + 1:] = 0

        return cleaned_B, cutoff_channel

    def remove_artifacts_group_subtraction(self, shielded_counts, self_transform, mismatch):
        new_shielded = shielded_counts.copy()
        divisions = 25
        start_point = 2  # seems to give good results
        old_bound = int(len(shielded_counts) * start_point / divisions)
        for plen in range(start_point, divisions):
            new_bound = int(len(shielded_counts) * plen / divisions)
            ratio = self.min_ratio(shielded_counts, self_transform, old_bound, new_bound)
            new_shielded[old_bound:new_bound] = shielded_counts[old_bound:new_bound] - mismatch[
                                                                                       old_bound:new_bound] * ratio
            old_bound = new_bound
        ratio = self.min_ratio(shielded_counts, self_transform, old_bound, len(shielded_counts))
        new_shielded[old_bound:] = shielded_counts[old_bound:] - mismatch[old_bound:] * ratio
        return new_shielded

    def process_matrices(self, null_responses, drf_responses, spec):
        """
        Reusable code for doing shielding application on a single spectrum
        :param null_responses:
        :param drf_responses:
        :param spec:
        :return:
        """
        T = self.get_T(*null_responses)
        return self.get_outcounts(T, drf_responses, spec)

    def min_ratio(self, shielded_counts, self_transform, old_bound, new_bound):
        """Utility function to help suppress oscillations"""
        if sum(self_transform[old_bound:new_bound]) == 0:
            return 1
        ratio = sum(shielded_counts[old_bound:new_bound]) / sum(self_transform[old_bound:new_bound])
        if abs(ratio) < 1:
            return ratio
        return 1

    def get_outcounts(self, T, drf_responses, spec):
        rebinned_counts = self.rebin_spec_todrf(spec)
        self_transform = self.iterative_matmul([drf_responses[1], drf_responses[0], rebinned_counts])
        mismatch = self_transform - rebinned_counts
        shielded_counts = self.iterative_matmul([drf_responses[1], T, drf_responses[0], rebinned_counts])
        # suppress oscillations using user-selected algorithm
        osc_reduction_algo = self.settings.getOscillationReductionAlgo()
        if osc_reduction_algo == 0:
            return self.rebin_spec_tomeasured(shielded_counts, (spec.ecal0, spec.ecal1,
                                                                     spec.ecal2, spec.ecal3))
        elif osc_reduction_algo == 1:
            shielded_counts = self.remove_artifacts_group_subtraction(shielded_counts, self_transform, mismatch)
            outcounts = self.rebin_spec_tomeasured(shielded_counts, (spec.ecal0, spec.ecal1,
                                                                     spec.ecal2, spec.ecal3))
        else:
            rebinned_shielded = self.rebin_spec_tomeasured(shielded_counts, (spec.ecal0, spec.ecal1,
                                                                     spec.ecal2, spec.ecal3))
            outcounts, cutoff = self.remove_artifacts_zeroing_peakfind(rebinned_counts, rebinned_shielded)
        return outcounts

    def add_to_database(self, baseSpectrum):
        session = Session()
        base_spectrum = session.query(BaseSpectrum).filter_by(detector_name=self.det_name,
                                                              material_name=baseSpectrum.material_name).first()
        if base_spectrum is None:
            session.add(baseSpectrum)
            session.commit()

    def add_to_detector(self, new_spectra):
        """
        Attach the shielded spectra to the detector
        """
        session = Session()
        detector = session.query(Detector).filter_by(name=self.det_name).first()
        for new_spec in new_spectra:
            self.add_to_database(new_spec)
            detector.base_spectra.append(new_spec)
        session.commit()
