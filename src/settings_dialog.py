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
This module allows user to change program settings such as the data directory
and sampling algorithm
"""

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QLabel, QComboBox

from src import sampling_algos
from src.rase_settings import RaseSettings
from .ui_generated import ui_prefs_dialog
import os
import sys
import inspect


class SettingsDialog(ui_prefs_dialog.Ui_PreferencesDialog, QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.settings = RaseSettings()
        self.setupUi(self)
        self.txtDataDir.setReadOnly(True)
        self.txtDataDir.setText(self.settings.getDataDirectory())
        self.dataDirectoryChanged = False
        self.algoDictionary = {}

        algoCount = 0

        for name, data in inspect.getmembers(sampling_algos, predicate=inspect.isfunction):
            try:
                readable_name = data.__doc__.splitlines()[0].strip()
                if readable_name == '':
                    raise Exception("")
            except:
                readable_name = name
            self.downSapmplingAlgoComboBox.addItem(readable_name)
            self.algoDictionary[algoCount] = data
            if data == self.settings.getSamplingAlgo():
                self.downSapmplingAlgoComboBox.setCurrentIndex(algoCount)
            algoCount += 1
        self.algorithmSelected = False
        self.downSapmplingAlgoComboBox.currentIndexChanged.connect(self.chooseSamplingAlgo)
        # add shielding oscillation reduction algorithm selector
        self.oscLabel = QLabel(self)
        self.oscLabel.setText(self.tr("Shielding Oscillation\nReduction Algorithm"))
        self.gridLayout.addWidget(self.oscLabel, 2, 0, 1, 1)
        self.oscComboBox = QComboBox(self)
        # options map to 0=None,1=Auto-Response Cancelling,2=Post-Peak Zeroing
        self.oscComboBox.addItems([self.tr("None"),
                                   self.tr("Auto-Response Cancelling"),
                                   self.tr("Post-Peak Zeroing")])
        # set saved value and connect change
        current = self.settings.getOscillationReductionAlgo()
        self.oscComboBox.setCurrentIndex(current)
        self.gridLayout.addWidget(self.oscComboBox, 2, 1, 1, 1)
        # move buttons down
        self.gridLayout.removeWidget(self.buttonBox)
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 3, Qt.AlignHCenter)

    @Slot(bool)
    def on_btnBrowseDataDir_clicked(self, checked):
        """
        Selects Data Directory
        """
        options = QFileDialog.ShowDirsOnly
        if sys.platform.startswith('win'): options = QFileDialog.DontUseNativeDialog
        dir = QFileDialog.getExistingDirectory(self, self.tr('Choose RASE Data Directory'),
                                               self.settings.getDataDirectory(), options)
        if dir:
            self.txtDataDir.setText(dir)
            self.dataDirectoryChanged = True

    def chooseSamplingAlgo(self, index):
        """
        Selects Sampling Algo
        """
        self.algorithmSelected = True


    @Slot()
    def accept(self):
        if self.dataDirectoryChanged:
            self.settings.setDataDirectory(os.path.normpath(self.txtDataDir.text()))
        idx = self.downSapmplingAlgoComboBox.currentIndex()
        if self.algorithmSelected:
            self.settings.setSamplingAlgo(self.algoDictionary[idx])
        # Persist new oscillation reduction algorithm selection
        osc_idx = self.oscComboBox.currentIndex()
        self.settings.setOscillationReductionAlgo(osc_idx)
        super().accept()
