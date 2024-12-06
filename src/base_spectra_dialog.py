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
This module allows import of instrument base spectra
"""
import logging
import os
import sys
import traceback
from os.path import splitext
import pandas as pd
from PySide6.QtCore import Qt, Slot, QAbstractTableModel, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QHeaderView, QApplication, QItemDelegate

from .spectrum_file_reading import readSpectrumFile, yield_spectra
from .spectrum_file_reading import all_spec as read_spec
from .rase_functions import get_or_create_material, get_ET_from_file
from .table_def import BaseSpectrum, BackgroundSpectrum, SecondarySpectrum, Session
from .ui_generated import ui_import_base_spectra_dialog
from .utils import profileit
from .rase_settings import RaseSettings

# translation_tag = 'bsp_d'


class BaseSpectraDialog(ui_import_base_spectra_dialog.Ui_Dialog, QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.model = BaseSpectraLoadModel()
        self.setupUi(self)
        self.tblSpectra.setModel(self.model)
        delegate = CheckBoxDelegate(None)
        self.tblSpectra.setItemDelegateForColumn(2, delegate)
        self.settings = RaseSettings()
        self.tblSpectra.hideColumn(2)
        self.tblSpectra.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.txtStatus.setText(self.model.text_status[-1])
        self.redColor = QColor(Qt.red)
        self.blackColor = QApplication.palette().base().color()

        # accessed outside dialog
        self.baseSpectra = []
        self.backgroundSpectrum = None
        self.backgroundSpectrumType = None
        self.ecal = None
        self.counts = None
        self.redColor = QColor(Qt.red)
        self.textColor = QApplication.palette().text().color()

    # Getters and setters to link with model
    @property
    def ecal(self):
        return self.model.ecal
    @ecal.setter
    def ecal(self, value):
        self.model.ecal = value

    @property
    def channel_count(self):
        return self.model.channel_count
    @channel_count.setter
    def channel_count(self, value):
        self.model.channel_count = value

    @property
    def baseSpectra(self):
        return self.model.baseSpectra
    @baseSpectra.setter
    def baseSpectra(self, value):
        self.model.baseSpectra = value

    @property
    def secondary_spectra(self):
        return self.model.secondary_spectra
    @secondary_spectra.setter
    def secondary_spectra(self, value):
        self.model.secondary_spectra = value

    @property
    def backgroundSpectrum(self):
        return self.model.backgroundSpectrum
    @backgroundSpectrum.setter
    def backgroundSpectrum(self, value):
        self.model.backgroundSpectrum = value

    @property
    def backgroundSpectrumType(self):
        return self.model.bgnd_spectrum_type
    @backgroundSpectrumType.setter
    def backgroundSpectrumType(self, value):
        self.model.bgnd_spectrum_type = value


    def appendtxtStatus(self, statstring):
        self.model.text_status.append(statstring)
        self.txtStatus.append(self.model.text_status[-1])

    def validate_spectra(self, spectra):
        """
        Validate same spectra length. NOT validating spectra have same ecal. This should be OK;
        we rebin to correct for it later if necessary.
        @param spectra:
        @return:
        """
        detectorchannellist = [rfo.counts.count(',') for rfo in spectra.values()]
        detectorchannelvalid = detectorchannellist.count(detectorchannellist[0]) == len(detectorchannellist)
        bkgchannelslist = [rfo.countsBckg.count(',') for rfo in spectra.values() if rfo.countsBckg is not None]
        ecalbkglist = [rfo.ecalBckg for rfo in spectra.values() if rfo.ecalBckg is not None]

        self.txtStatus.setTextColor(self.redColor)
        if not detectorchannelvalid:
            self.appendtxtStatus(self.tr('Mismatch in # of channels between spectra'))
        self.txtStatus.setTextColor(self.textColor)
        if bkgchannelslist:
            bkgchannelsvalid = bkgchannelslist.count(bkgchannelslist[0]) == len(bkgchannelslist)
            if not bkgchannelsvalid:
                self.appendtxtStatus(self.tr('Mismatch in # of channels between background spectra'))
        if ecalbkglist:
            ecalbkgvalid = ecalbkglist.count(ecalbkglist[0]) == len(ecalbkglist)
            if not ecalbkgvalid:
                self.appendtxtStatus(self.tr('Mismatch in energy calibration parameters between background spectra'))

    @Slot(bool)
    def on_btnBrowse_clicked(self, checked, directoryPath = None, secType = None):
        """
        Selects base spectra
        :param directoryPath: optional path input
        :param secType: optional secondary spectrum type
        """
        self.model.sourcedir = directoryPath
        if self.model.sourcedir is None:
            options = QFileDialog.ShowDirsOnly
            if sys.platform.startswith('win'): options = QFileDialog.DontUseNativeDialog
            self.model.sourcedir = QFileDialog.getExistingDirectory(self, self.tr('Choose Base Spectra Directory'),
                                            self.settings.getDataDirectory(), options)
        if self.model.sourcedir:
            self.txtFilepath.setText(self.model.sourcedir)
            self.model.reset_data()
            filenames = self.model.get_file_names(self.model.sourcedir)
            if not filenames:
                QMessageBox.critical(self, self.tr('Invalid Directory Selection'), self.tr(
                                                                                'No n42 files in selected directory'))
                return
            try:
                self.model.get_spectra_data(self.model.sourcedir, filenames)  #read the spectra into memory
            except Exception as e:
                traceback.print_exc()
                logging.exception(self.tr('Handled Exception'), exc_info=True)

            self.validate_spectra(self.model.specMap)  # All beautification, fine to stay in view

            # populate material, filename table
            self.tblSpectra.blockSignals(True)
            self.appendtxtStatus(self.tr('Number of base spectra read = ') + str(self.model.rowCount(None)))
            if self.model.sharedObject:
                if self.model.sharedObject.chanDataType:
                    self.appendtxtStatus(self.tr('Channel data type is ') + self.model.sharedObject.chanDataType)
                if self.model.sharedObject.bkgndSpectrumInFile:
                    self.appendtxtStatus(self.tr('Secondary spectrum found in file'))
            self.tblSpectra.blockSignals(False)
            self.tblSpectra.resizeColumnsToContents()
            self.tblSpectra.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

            # Check with the user about the type of the secondary spectrum
            self.tblSpectra.showColumn(2)
            if self.model.sharedObject.bkgndSpectrumInFile:
                if len(self.model.secondary_spectra) > 1:
                    self.txtStatus.append(self.tr('Secondary spectra identified in base spectra files.'))
                else:
                    self.txtStatus.append(self.tr('Secondary spectrum identified in base spectra files.'))
                no_known_classcode = True
                for secondary in self.model.secondary_spectra:
                    if type(secondary.classcode) == str:
                        if secondary.classcode.lower() == 'foreground':
                            self.appendtxtStatus(self.tr('An additional foreground was identified.'))
                            no_known_classcode = False
                        elif secondary.classcode.lower() == 'calibration':
                            self.appendtxtStatus(self.tr('An internal calibration source spectrum was identified.'))
                            no_known_classcode = False
                        elif secondary.classcode.lower() == 'intrinsicactivity':
                            self.appendtxtStatus(self.tr('An intrinsic activity spectrum was identified.'))
                            no_known_classcode = False
                        elif secondary.classcode.lower() == 'background':
                            self.appendtxtStatus(self.tr('A background spectrum was identified.'))
                            no_known_classcode = False
                        elif secondary.classcode.lower() == 'notspecified':
                            self.appendtxtStatus(self.tr('A spectrum with an unspecified classcode was identified.'))
                if no_known_classcode:
                    self.appendtxtStatus(self.tr('Could not determine type of secondary spectrum.'))
                self.model.backgroundSpectrumType = 0


    @profileit
    @Slot()
    def accept(self):
        try:
            # check that all material names are filled
            if not self.model.check_material_names():
                QMessageBox.warning(self, self.tr('Empty Material Names'), self.tr(
                                                                    'Must have a material name for each element'))
            else:
                self.model.accept()

        except Exception as e:
              traceback.print_exc()
              logging.exception(self.tr('Handled Exception'), exc_info=True)

        return QDialog.accept(self)


class BaseSpectraLoadModel(QAbstractTableModel):

    def __init__(self, data=None,  *args, **kwargs):
        super(BaseSpectraLoadModel, self).__init__(*args, **kwargs)
        self._colheaders = [self.tr('Material Name'), self.tr('File Name'), self.tr('Include\nIntrinsic Source?')]
        self._data = data or self._set_empty_data()
        self.baseSpectra = []
        self.bgnd_spectrum_type = None
        self.bckgrndCorrupted = False
        self.sharedObject = self._set_shared_object(args)
        self.secondary_types = [self.tr('Background Spectrum'), self.tr('Internal Calibration Spectrum')]
        self.secondary_spectra = []
        self.backgroundSpectrumType = None
        self.text_status = ['']  # Cumbersome, but necessary for readSpectrumFile to work right
        self.specMap = {}
        self.channel_count = None
        self.ecal = None
        self.sourcedir = ''

    def _assign_data(self, newSpecs):
        self.layoutAboutToBeChanged.emit()
        for filename in newSpecs.keys():
            # TODO: develop more elaborated algorithm to correctly import thing like "HEU" or
            #  "WGPu" w/o altering the capitalization
            matName = '-'.join(splitext(filename)[0].split('_')[2:])
            self._data.loc[len(self._data.index)] = [matName, filename, False]
        self.layoutChanged.emit()

    def _set_empty_data(self):
        df = pd.DataFrame(columns=self._colheaders)
        return df

    def _set_shared_object(self, args):
        if len(args) > 0:
            try:
                if not isinstance(args[0], bool):
                    raise TypeError
            except TypeError as e:
                traceback.print_exc()
                logging.exception(self.tr('Handled Exception: Attempting to manually define sharedObject but shared '
                                        'object argument is not a boolean. Setting to default "True"'), exc_info=True)
        if len(args) > 0 and isinstance(args[0], bool):
            return SharedObject(args[0])
        else:
            return SharedObject(True)

    def data(self, index, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._data.iloc[index.row(), index.column()]

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if role == Qt.EditRole and index.column() == 0:
            self._data.iloc[index.row(), index.column()] = value
        if role == Qt.CheckStateRole and index.column() == 2:
            self._data.iloc[index.row(), index.column()] = value
        else:
            return False

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        # TODO: necessary?
        return self._data.shape[1]

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

    def flags(self, index):  # Qt was imported from PyQt4.QtCore
        if index.column() == 0:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        elif index.column() == 2:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def get_file_names(self, dir):
        return [f for f in os.listdir(dir) if f.lower().endswith('.n42')]

    def get_spectra_data(self, dir, filenames=None):
        newSpecs = {}
        if self.sourcedir is None:
            self.sourcedir = dir
        if filenames is None:
            filenames = self.get_file_names(dir)
        try:
            firstroot = get_ET_from_file(dir + os.sep + filenames[0]).getroot()
            spectra = yield_spectra(firstroot, read_spec)
            self.secondary_spectra = [spec for spec in spectra if isinstance(spec, SecondarySpectrum)]
        except Exception as e:
            pass

        for filename in filenames:
            try:
                counts, ecal, realtime, livetime, rase_sensitivity, flux_sensitivity, countsBckg, ecalBckg,\
                                        realtimeBckg, livetimeBckg, neutrons, neutron_sensitivity = readSpectrumFile(
                                        os.path.join(dir, filename), self.sharedObject, self.text_status,
                                        requireRASESen=True, only_one_secondary=self.secondary_spectra is None)

                newSpecs[filename] = ReadFileObject(counts, ecal, realtime, livetime, rase_sensitivity,
                                                    flux_sensitivity, countsBckg, ecalBckg, realtimeBckg, livetimeBckg,
                                                    neutrons, neutron_sensitivity)
                # TODO: replace background elements of the RFO with the background from the
                # secondary spectra list if it's present
            except ValueError:
                pass

        self.channel_count = len(newSpecs[filenames[0]].counts.split(','))
        self.ecal = newSpecs[filenames[0]].ecal
        #
        background_sec = [spec for spec in self.secondary_spectra if spec.classcode == 'Background']
        if len(background_sec):
            first_bgs = background_sec[0]
            newSpecs[filenames[0]].countsBckg = first_bgs.baseCounts
            newSpecs[filenames[0]].ecalBckg = list(float(k) for k in
                                                       first_bgs.ecal[:len(newSpecs[filenames[0]].ecalBckg)])
            newSpecs[filenames[0]].livetimeBckg = first_bgs.livetime
            newSpecs[filenames[0]].realtimeBckg = first_bgs.realtime

        self._assign_data(newSpecs)
        for key, val in newSpecs.items():
            self.specMap[key] = val

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self._data = self._set_empty_data()
        self.layoutChanged.emit()

    def check_material_names(self):
        if len(self._data[self._data[self._colheaders[0]] == ''].index) > 0:
            return False
        else:
            return True

    def accept(self):
        session = Session()
        if self.sharedObject.bkgndSpectrumInFile:  # and self.bgnd_spectrum_type is not None:
            rfos = [self.specMap[str(self._data.iloc[row, 1])] for row in range(self.rowCount(None))]
            indices = [i for i, r in enumerate(rfos) if r.realtimeBckg is not None and r.livetimeBckg is not None]
            if len(indices) == 0:
                self.bckgrndCorrupted = True
            else:
                background_index = indices[0]
        self.intrinsic_is_included = False
        self.backgroundSpectrum = None
        for row in range(self.rowCount(None)):
            # initialize a BaseSpectrum
            materialName = str(self._data.iloc[row, 0])
            # print(materialName)
            include_instrinsic = bool(self._data.iloc[row, 2])
            material = get_or_create_material(session, materialName, include_instrinsic)
            self.intrinsic_is_included = self.intrinsic_is_included or include_instrinsic
            baseSpectraFilename = str(self._data.iloc[row, 1])
            baseSpectraFilepath = os.path.join(self.sourcedir, baseSpectraFilename)
            if 'n42' not in baseSpectraFilepath.lower():
                continue

            rfo = self.specMap[baseSpectraFilename]

            if self.sharedObject.bkgndSpectrumInFile and not self.bckgrndCorrupted and row >= background_index:
                if row == background_index:
                     # sets default background to first in list
                    self.backgroundSpectrum = BackgroundSpectrum(material=material,
                                                                 filename=baseSpectraFilepath,
                                                                 realtime=rfo.realtimeBckg,
                                                                 livetime=rfo.livetimeBckg,
                                                                 baseCounts=rfo.countsBckg,
                                                                 ecal=rfo.ecalBckg)
                elif self.backgroundSpectrum.livetime != rfo.livetimeBckg and rfo.livetimeBckg is not None:
                    if rfo.livetimeBckg > self.backgroundSpectrum.livetime:
                        self.backgroundSpectrum = BackgroundSpectrum(material=material,
                                                                     filename=baseSpectraFilepath,
                                                                     realtime=rfo.realtimeBckg,
                                                                     livetime=rfo.livetimeBckg,
                                                                     baseCounts=rfo.countsBckg,
                                                                     ecal=rfo.ecalBckg)

            baseSpectrum = BaseSpectrum(material=material, filename=baseSpectraFilepath,
                                        realtime=rfo.realtime,
                                        livetime=rfo.livetime,
                                        rase_sensitivity=rfo.rase_sensitivity,
                                        flux_sensitivity=rfo.flux_sensitivity,
                                        baseCounts=rfo.counts, ecal=rfo.ecal, neutrons=rfo.neutrons,
                                        neutron_sensitivity=rfo.neutron_sensitivity)

            self.baseSpectra.append(baseSpectrum)


class CheckBoxDelegate(QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
    Taken directly from Drew's May 13, 2018 answer on Stack Exchange:
    https://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
    """
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        Important, otherwise an editor is created if the user clicks in this cell.
        """
        return None

    def paint(self, painter, option, index):
        """
        Paint a checkbox without the label.
        """
        #TODO: Center the checkbox and make it pretty. Also make it so you have to click the
        # checkbox, not the whole cell
        self.drawCheck(painter, option, option.rect, Qt.Unchecked if bool(index.data()) is False else Qt.Checked)

    def editorEvent(self, event, model, option, index):
        '''
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton and this cell is editable. Otherwise do nothing.
        '''
        checkable = index.flags() & Qt.ItemIsUserCheckable
        if not int(checkable.value) > 0:
            return False
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # Change the checkbox-state
            self.setModelData(None, model, index)
            return True
        return False

    def setModelData (self, editor, model, index):
        '''
        The user wanted to change the old state in the opposite.
        '''
        model.setData(index, True if bool(index.data()) == 0 else False, Qt.CheckStateRole)


class SharedObject:
    def __init__(self, isBckgrndSave):
        self.isBckgrndSave = isBckgrndSave
        self.chanDataType = None
        self.bkgndSpectrumInFile = False


class ReadFileObject:
    def __init__(self, counts, ecal, realtime, livetime, rase_sensitivity, flux_sensitivity, countsBckg=None,
                    ecalBckg=None, realtimeBckg=None, livetimeBckg=None, neutrons=0, neutron_sensitivity=0):
        self.counts = counts
        self.ecal = ecal
        self.realtime = realtime
        self.livetime = livetime
        self.rase_sensitivity = rase_sensitivity
        self.flux_sensitivity = flux_sensitivity
        self.countsBckg = countsBckg
        self.ecalBckg = ecalBckg
        self.realtimeBckg = realtimeBckg
        self.livetimeBckg = livetimeBckg
        self.neutrons = neutrons
        self.neutron_sensitivity = neutron_sensitivity
