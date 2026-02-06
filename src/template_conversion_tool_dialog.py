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
This module allows users to convert one set of spectra in one format to another
"""
import os

from src.base_building_algos import default_config, pcf_config
from src.create_base_spectra_dialog import load_configs_from_file
from src.rase_settings import RaseSettings
from src.ui_generated import ui_template_conversion_dialog

from PySide6.QtCore import Qt, Slot, QAbstractListModel, QModelIndex
from PySide6.QtWidgets import QDialog, QMessageBox, QFileDialog, QDataWidgetMapper, QLineEdit


class TemplateConversionDialog(ui_template_conversion_dialog.Ui_dialogTemplateConversion, QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.model_lineedits = [self.txtConfigPath, self.txtTemplatePath, self.txtInputPath, self.txtOutputPath]
        self.model = TemplateConversionModel()
        self.setup_combo()

        self.mapper = QDataWidgetMapper()
        self.mapper.setModel(self.model)
        self.set_modelmap(self.mapper, self.model_lineedits, range(1,5))
        self.mapper.toFirst()

        self.cmbInputTemplate.currentTextChanged.connect(lambda: self.model.setData(self.model.fields[
                                                        'input_data_format'], self.cmbInputTemplate.currentText()))
        self.txtConfigPath.textChanged.connect(lambda: self.model.setData(self.model.fields[
                                                        'path_input_config'], self.txtConfigPath.text()))
        self.txtConfigPath.textChanged.connect(self.setup_combo)


    def set_modelmap(self, mapper, viewvals, modelvals):
        """
        Function for linking the view to update from the model data
        :param mapper: QDataWidgetMapper
        :param viewvals: iterable of line edit objects
        :param modelvals: iterable of column indices in model
        :return:
        """
        for w, c in zip(viewvals, modelvals):
            mapper.addMapping(w, c)

    def handleEditingFinished(self):
        """
        Utility function that makes sure all the line edits are set to the model
        :return:
        """
        linetexts = [lineedit.text() if type(lineedit) ==
                     QLineEdit else lineedit.toPlainText() for lineedit in self.model_lineedits]
        for linetext, line_edit in zip(linetexts, self.model_lineedits):
            column = self.model_lineedits.index(line_edit) + 1
            self.model.setData(self.model.index(0, column), linetext, Qt.EditRole)

    def setup_combo(self):
        """
        Configures the contents of the combo box
        :return:
        """
        self.cmbInputTemplate.clear()
        configs = {**default_config, **pcf_config}
        if self.model.data(self.model.fields['path_input_config']):
            file_configs = load_configs_from_file(self, self.model.data(self.model.fields['path_input_config']))
            configs = {**configs, **file_configs}
        self.cmbInputTemplate.addItems([key for key in configs.keys() if type(key)==str])

    @Slot(bool)
    def on_btnInputConfig_clicked(self, checked, directory_path=None):
        """
        Selects the input config file
        :param checked: automatic from signal
        :param directory_path: optional path input
        :return:
        """
        self.handleEditingFinished()
        dir_path = directory_path if directory_path is not None else os.path.dirname(
            self.model.settings.getBaseSpectrumCreationConfig()) # path to the default bsc yaml
        filepath = self.select_file(dir_path, 'YAML(*.yaml)')
        if filepath:
            self.model.setData(self.model.fields['path_input_config'], filepath)
            self.setup_combo()

    @Slot(bool)
    def on_btnOutputTemplate_clicked(self, checked, directory_path=None):
        """
        Selects the input config file
        :param checked: automatic from signal
        :param directory_path: optional path input
        :return:
        """
        self.handleEditingFinished()
        dir_path = directory_path if directory_path is not None else self.model.settings.getN42TemplatePath()
        filepath = self.select_file(dir_path,'Spectrum formatted files (*.n42 *.xml *.json);;All Files (*)')
        if filepath:
            self.model.setData(self.model.fields['path_output_template'], filepath)

    @Slot(bool)
    def on_btnInputFolder_clicked(self, checked, directory_path=None):
        """
        Selects the input config file
        :param checked: automatic from signal
        :param directory_path: optional path input
        :return:
        """
        self.handleEditingFinished()
        dir_path = directory_path if directory_path is not None else self.model.settings.getLastDirectory()
        folder_path = self.select_folder(dir_path)
        if folder_path:
            self.model.setData(self.model.fields['path_input_folder'], folder_path)

    @Slot(bool)
    def on_btnOutputFolder_clicked(self, checked, directory_path=None):
        """
        Selects the input config file
        :param checked: automatic from signal
        :param directory_path: optional path input
        :return:
        """
        self.handleEditingFinished()
        dir_path = directory_path if directory_path is not None else self.model.settings.getLastDirectory()
        folder_path = self.select_folder(dir_path)
        if folder_path:
            self.model.setData(self.model.fields['path_output_folder'], folder_path)

    
    def select_file(self, directory_path: str, file_filter: str):
        """
        Utility function for selecting files only
        :param directory_path: optional path input
        :return:
        """
        selected_file, _ = QFileDialog.getOpenFileName(self, self.tr('Select a File'),
                                                       directory_path, file_filter)
        return selected_file

    def select_folder(self, directory_path: str):
        """
        Utility function for selecting folders only
        :param directory_path: optional path input
        :return:
        """
        options = QFileDialog.ShowDirsOnly
        selected_folder = QFileDialog.getExistingDirectory(self, self.tr('Select a Directory'),
                                                                directory_path, options)
        return selected_folder

    @Slot()
    def accept(self):
        self.handleEditingFinished()
        try:
            failed_files = self.model.accept()
            if failed_files:
                completed_message = self.tr('Files not converted: \n\n  -- ') + '\n  -- '.join(failed_files)
            else:
                completed_message = ''
            QMessageBox.information(self, self.tr('Processing completed'),
                                    self.tr('Processing completed. ') + completed_message)
            # return QDialog.accept(self)
        except Exception as e:
            QMessageBox.critical(self, self.tr('Exception'), f'{e}')
            return


class TemplateConversionModel(QAbstractListModel):

    def __init__(self, *args, **kwargs):
        super(TemplateConversionModel, self).__init__(*args, **kwargs)
        self.settings = RaseSettings()
        self._data = ['', '', '', '', '']
        self.fields = {'input_data_format': self.index(0, 0),
                       'path_input_config': self.index(0, 1),
                       'path_output_template': self.index(0, 2),
                       'path_input_folder': self.index(0, 3),
                       'path_output_folder': self.index(0, 4)}
        self.reset_data()

    @property
    def model_data(self):
        """
        For API use, simply returns the list
        :return:
        """
        return self._data  #TODO: should these calls be copies to avoid direct editing of _data?

    def set_val(self, key, value):
        """
        API call to assign data values and use capability
        :param key: str, one of the fields keys
        :param value: str
        :return:
        """
        self.setData(self.fields[key], value)

    def reset_data(self):
        """
        Initialize the data based on global RASE settings
        :return:
        """
        self.setData(self.fields['path_input_config'], self.settings.getBaseSpectrumCreationConfig())
        self.setData(self.fields['input_data_format'], list(default_config.keys())[0])


    ######### below this point are generic model functions #########
    def rowCount(self, index=None):
        return 1

    def columnCount(self, parent=None):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._data[index.column()])

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            self._data[index.column()] = value
            self.update_data()
            return True
        return False

    def index(self, row, column, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self._data
        else:
            return QModelIndex()
        if column < len(parentItem):
            return self.createIndex(0, column, parentItem)
        return QModelIndex()

    def update_data(self):
        self.dataChanged.emit(self.index(0, 0), self.index(0, self.columnCount() - 1))

    def accept(self):
        if '' in self._data:
            raise Exception(self.tr('Exception: All fields must be filled'))
        if not os.path.isdir(self._data[self.fields['path_input_folder'].column()]):
            raise Exception(self.tr('Exception: Input path is not a folder'))
        if not os.path.isdir(self._data[self.fields['path_output_folder'].column()]):
            raise Exception(self.tr('Exception: Output path is not a folder'))

        from mako.template import Template
        from src.rase_functions import get_ET_from_file
        from src.base_building_algos import get_ET_values, build_base_ET, write_base_text
        import yaml

        try:
            built_in_configs = {**default_config, **pcf_config}
            with open(self._data[self.fields['path_input_config'].column()], 'r') as file:
                file_configs = yaml.safe_load(file)
            file_configs = {**built_in_configs, **file_configs}
            config = file_configs[self._data[self.fields['input_data_format'].column()]]
        except:
            raise Exception(self.tr('Exception: Input format config file could not be read'))

        folderpath = self._data[self.fields['path_input_folder'].column()]
        failed_files = []
        for inputfile in [f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))]:
            try:
                ET = get_ET_from_file(os.path.join(folderpath, inputfile))
                values = get_ET_values(ET=ET, measureXPath=config['measurement_spectrum_xpath'],
                                          realtimeXPath=config['realtime_xpath'], livetimeXPath=config['livetime_xpath'],
                                          calibration=config['calibration'], additionals=config.get('additionals'),
                                          secondaries_dict=config.get('secondaries'))

                template = Template(filename=self._data[self.fields['path_output_template'].column()],
                                    input_encoding='utf-8', strict_undefined=True)
                output = build_base_ET(rawValues=values, device_template=template)
                output_file_name = f'templated_{inputfile}'
                # no detailed information about /why/ it failed; rely on the user to know if there is a secondary spec requirement
                write_base_text(output, self._data[self.fields['path_output_folder'].column()], output_file_name)
            except:
                failed_files.append(inputfile)
        return failed_files


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    w = QApplication()
    TemplateConversionDialog().exec()

