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
Dialog functionality for removing isotope ID results from existing files
"""
from pathlib import Path

from src.rase_functions import remove_xmlblock
from src.rase_settings import RaseSettings
from src.ui_generated import ui_remove_idresults_dialog

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QMessageBox, QFileDialog, QLineEdit, QDialogButtonBox
import traceback

class StripResultsDialog(ui_remove_idresults_dialog.Ui_RemoveIDsDialog, QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.settings = RaseSettings()
        self.btnInputDir.clicked.connect(lambda: self.browse_directory(self.txtInputDir))
        self.btnOutputDir.clicked.connect(lambda: self.browse_directory(self.txtOutputDir))
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.txtInputDir.textChanged.connect(self.validate_inputs)
        self.txtOutputDir.textChanged.connect(self.validate_inputs)

    def browse_directory(self, dir_lineedit: QLineEdit):
        dir_path = Path(dir_lineedit.text())
        if not dir_path.is_dir():
            dir_path = Path(self.settings.getLastDirectory())
        options = QFileDialog.ShowDirsOnly
        selected_folder = QFileDialog.getExistingDirectory(self, self.tr('Select a Directory'),
                                                                str(dir_path), options)
        dir_lineedit.setText(selected_folder)

    def validate_inputs(self):
        input_dir = self.txtInputDir.text().strip()
        output_dir = self.txtOutputDir.text().strip()
        valid = (input_dir is not '') and (output_dir is not '') and Path(input_dir).is_dir() and Path(output_dir).is_dir()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(valid)

    @Slot()
    def accept(self):
        in_dir = Path(self.txtInputDir.text())
        out_dir = Path(self.txtOutputDir.text())

        try:
            n_converted, n_copied = remove_xmlblock(in_dir, out_dir)
            QMessageBox.information(self, self.tr('Processing completed'), self.tr('Conversion complete: converted '
                                       '{} files, copied {} unconverted files').format(n_converted, n_copied))
        except FileNotFoundError:
            QMessageBox.warning(self, self.tr('Error'), traceback.format_exc())


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    w = QApplication()
    StripResultsDialog().exec()