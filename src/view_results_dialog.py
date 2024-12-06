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
This module displays the complete summary of replay results and subsequent analysis
"""
import logging
import traceback

import numpy as np
import pandas as pd

from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

from PySide6.QtCore import Slot, QAbstractTableModel, Qt, QSize, QPoint, QCoreApplication
from PySide6.QtGui import QColor, QAbstractTextDocumentLayout, QTextDocument, QKeySequence, \
    QAction, QValidator
from PySide6.QtWidgets import QDialog, QMessageBox, QHeaderView, QFileDialog, QCheckBox, \
    QVBoxLayout, QDialogButtonBox, QStyledItemDelegate, QApplication, QStyle, QMenu, QTableWidget, \
    QTableWidgetItem, QWidget

from src.plotting import ResultPlottingDialog, Result3DPlottingDialog
from .qt_utils import DoubleValidator
from src.results_calculation import compute_freq_results, export_results, calculateScenarioStats
from .ui_generated import ui_results_dialog
from src.detailed_results_dialog import DetailedResultsDialog
from src.correspondence_table_dialog import CorrespondenceTableDialog
from src.manage_weights_dialog import ManageWeightsDialog
from src.rase_settings import RaseSettings
from src.help_dialog import HelpDialog

# translation_tag = 'vres_d'

NUM_COL = 16
INST_REPL, SCEN_ID, SCEN_DESC, ACQ_TIME, REPL, INFL, PD, PD_CI, TP, FP, FN, CANDC, CANDC_CI, \
PRECISION, RECALL, FSCORE = range(NUM_COL)

# color scale from https://colorbrewer2.org/#type=diverging&scheme=RdYlGn&n=11
STOPLIGHT_COLORS = ['#a50026', '#d73027', '#f46d43', '#fdae61', '#fee08b', '#ffffbf', '#d9ef8b',
                    '#a6d96a', '#66bd63', '#1a9850', '#006837']

COLS = [QCoreApplication.translate('vres_d', 'Det/Replay'), QCoreApplication.translate('vres_d', 'Scen Desc'),
    QCoreApplication.translate('vres_d', 'Dose'), QCoreApplication.translate('vres_d', 'BkgDose'),
    QCoreApplication.translate('vres_d', 'Flux'), QCoreApplication.translate('vres_d', 'BkgFlux'),
    QCoreApplication.translate('vres_d', 'Infl'), QCoreApplication.translate('vres_d', 'AcqTime'),
    QCoreApplication.translate('vres_d', 'Repl'), QCoreApplication.translate('vres_d', 'Comment'),
    QCoreApplication.translate('vres_d', 'PID'), QCoreApplication.translate('vres_d', 'PID CI'),
    QCoreApplication.translate('vres_d', 'PFID'), QCoreApplication.translate('vres_d', 'C&C'),
    QCoreApplication.translate('vres_d', 'C&C CI'), QCoreApplication.translate('vres_d', 'TP'),
    QCoreApplication.translate('vres_d', 'FP'), QCoreApplication.translate('vres_d', 'FN'),
    QCoreApplication.translate('vres_d', 'Precision'), QCoreApplication.translate('vres_d', 'Recall'),
    QCoreApplication.translate('vres_d', 'F_Score'), QCoreApplication.translate('vres_d', 'wTP'),
    QCoreApplication.translate('vres_d', 'wFP'), QCoreApplication.translate('vres_d', 'wFN'),
    QCoreApplication.translate('vres_d', 'wPrecision'), QCoreApplication.translate('vres_d', 'wRecall'),
    QCoreApplication.translate('vres_d', 'wF_Score')]

class ResultsTableModel(QAbstractTableModel):
    """Table Model for the Identification Results

    The underline data is the pandas dataframe produced in rase.py.
    The input dataframe is copied as some of the formatting applied does not need to propagate to the original

    :param data: the new input pandas dataframe from the identification results analysis
    """
    def __init__(self, data):
        super(ResultsTableModel, self).__init__()
        self._data = data.copy()
        self.col_settings = RaseSettings().getResultsTableSettings()
        self._reformat_data()

    def _reformat_data(self):
        """
        Reformat underlying data for prettier display and downselect only the columns requested by the user
        """
        self._data['Det/Replay'] = self._data['Det'] + '/' + self._data['Replay']
        self._data['PID CI'] = [str(round(abs(l), 2)) + ' - ' + str(round(h, 2)) for h, l in
                                zip(self._data['PID_H'], self._data['PID_L'])]
        self._data['C&C CI'] = [str(round(abs(l), 2)) + ' - ' + str(round(h, 2)) for h, l in
                                zip(self._data['C&C_H'], self._data['C&C_L'])]
        # self._data.drop(columns=['Det', 'Replay', 'PID_L', 'PID_H', 'C&C_L', 'C&C_H'], inplace=True)
        mat_cols = [s for s in self._data.columns.to_list() if (s.startswith('Dose_') or s.startswith('Flux_'))]
        bkg_cols = [s for s in self._data.columns.to_list() if (s.startswith('BkgDose_') or s.startswith('BkgFlux_'))]

        cols = ['Det/Replay', 'Scen Desc'] + mat_cols + bkg_cols + ['Infl', 'AcqTime', 'Repl',
                                        'Comment', 'PID', 'PID CI', 'PFID', 'C&C', 'C&C CI',
                                        'TP', 'FP', 'FN', 'Precision', 'Recall', 'F_Score',
                                        'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']

        if self.col_settings:
            cols = [c for c in cols if (c.startswith('Dose') or c.startswith('BkgDose') or
                        c.startswith('Flux') or c.startswith('BkgFlux')) or c in self.col_settings]
            if 'Dose' not in self.col_settings:
                cols = [c for c in cols if not c.startswith('Dose')]
            if 'Background Dose' not in self.col_settings:
                cols = [c for c in cols if not c.startswith('BkgDose')]
            if 'Flux' not in self.col_settings:
                cols = [c for c in cols if not c.startswith('Flux')]
            if 'Background Flux' not in self.col_settings:
                cols = [c for c in cols if not c.startswith('BkgFlux')]
        self._data = self._data[cols]
        # self._data = self._data.rename(columns={'PID':'Prob. ID'})

    def reset_data(self, data):
        """
        Reset and reformat the data.
        Should be called always after the data have been recomputed or columns selection changed
        :param data: the new input pandas dataframe from the identification results analysis
        """
        self.layoutAboutToBeChanged.emit()
        self._data = data.copy()
        self.col_settings = RaseSettings().getResultsTableSettings()
        self._reformat_data()
        self.layoutChanged.emit()

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return f'{value:.3g}'
            else:
                return str(value)

        if role == Qt.DecorationRole:
            # stopchart blocks
            if self._data.columns[index.column()] in ['PID', 'C&C', 'F_Score', 'wF_Score']:
                value = self._data.iloc[index.row(), index.column()]
                if value < 0: value = 0
                if value > 1: value = 1
                value = int(value * (len(STOPLIGHT_COLORS) - 1))
                return QColor(STOPLIGHT_COLORS[value])

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                h = str(self._data.columns[section]).split('_')
                if h[0] == "Dose" or h[0] == "BkgDose" or h[0] == "Flux" or h[0] == "BkgFlux":
                    desc = "".join(h[1:]).split('-')
                    return f'{self.tr(h[0])}\n{desc[0]}\n{"".join(desc[1:])}'
                else:
                    return self.tr(self._data.columns[section])
            # if orientation == Qt.Vertical:
            #     print(self._data.index[section].detector.name)
            #     return (f"{self._data.index[section].detector.id} * "
            #             f"{self._data.index[section].replay.id} * "
            #             f"{self._data.index[section].bkg.id} * ")
        if role == Qt.UserRole:
            if orientation == Qt.Vertical:
                return self._data.index[section]

    def sort(self, column: int, order: Qt.SortOrder = ...) -> None:
        self.layoutAboutToBeChanged.emit()
        if len(self._data.columns):
            self._data.sort_values(by=[self._data.columns[column]], ascending=not order, inplace=True)
        self.layoutChanged.emit()

    def scenario_desc_col_index(self):
        if 'Scen Desc' in self._data.columns:
            return self._data.columns.values.tolist().index('Scen Desc')
        return None


class ViewResultsDialog(ui_results_dialog.Ui_dlgResults, QDialog):
    """Dialog to display identification results and select variables for plotting

    :param parent: the parent dialog
    """
    def __init__(self, parent, sim_context_list):

        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.parent = parent
        self.sim_context_list = sim_context_list

        self.result_super_map, self.scenario_stats_df = calculateScenarioStats(sim_context_list, gui=self)

        self.help_dialog = None
        self.comboListXY = ['', 'Det', 'Replay', 'Source Dose', 'Source Flux', 'Distance (given dose)',
                     'Distance (given flux)', 'Background Dose', 'Background Flux', 'Infl',
                     'AcqTime', 'Repl', 'PID', 'PFID', 'C&C', 'TP', 'FP', 'FN', 'Precision',
                     'Recall', 'F_Score', 'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']
        self.cmbXaxis.addItems(self.tr(c) for c in self.comboListXY)
        self.cmbYaxis.addItems(self.tr(c) for c in self.comboListXY)
        self.comboListZ = ['', 'PID', 'PFID', 'C&C', 'TP', 'FP', 'FN', 'Precision', 'Recall',
                        'F_Score', 'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']
        self.cmbZaxis.addItems(self.tr(c) for c in self.comboListZ)
        self.comboListGrp = ['', 'Det', 'Replay', 'Source Material', 'Background Material', 'Infl',
                     'AcqTime', 'Repl', 'PID', 'PFID', 'C&C', 'TP', 'FP', 'FN', 'Precision',
                     'Recall', 'F_Score', 'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']
        self.cmbGroupBy.addItems(self.tr(c) for c in self.comboListGrp)
        self.cmbGroupBy.setEnabled(False)

        for wdgt in [getattr(self, f'txtRef{l}{a}') for a in ['X', 'Y'] for l in ['Dose', 'Distance']]:
            wdgt.setValidator(DoubleValidator(wdgt))
            wdgt.textChanged.connect(self.set_view_plot_btn_status)
            wdgt.validator().setBottom(1.e-6)
            wdgt.validator().validationChanged.connect(self.handle_validation_change)

        self.matNames_dose = ["".join(s.split("_")[1:]) for s in self.scenario_stats_df.columns.to_list()
                              if s.startswith('Dose_')]
        self.matNames_flux = ["".join(s.split("_")[1:]) for s in self.scenario_stats_df.columns.to_list()
                              if s.startswith('Flux_')]
        self.bkgmatNames_dose = ["".join(s.split("_")[1:]) for s in self.scenario_stats_df.columns.to_list()
                                 if s.startswith('BkgDose_')]
        self.bkgmatNames_flux = ["".join(s.split("_")[1:]) for s in self.scenario_stats_df.columns.to_list()
                                 if s.startswith('BkgFlux_')]

        self.names_dict = {'Source Dose': self.matNames_dose, 'Source Flux': self.matNames_flux,
                           'Distance (given dose)': self.matNames_dose,
                           'Distance (given flux)': self.matNames_flux,
                           'Background Dose': self.bkgmatNames_dose,
                           'Background Flux': self.bkgmatNames_flux}
        self.btnViewPlot.setEnabled(False)
        self.btnFreqAnalysis.setEnabled(False)

        self.btnInfoDistanceX.clicked.connect(self.open_help)
        self.btnInfoDistanceY.clicked.connect(self.open_help)

        self.btnClose.clicked.connect(self.closeSelected)
        self.buttonExportCSV.clicked.connect(lambda: self.handleExport('csv'))
        self.buttonExportJSON.clicked.connect(lambda: self.handleExport('json'))
        self.buttonCorrTable.clicked.connect(lambda: self.openCorrTable())
        self.buttonManageWeights.clicked.connect(lambda: self.openWeightsTable())
        self.btnFreqAnalysis.clicked.connect(self.show_freq_results)

        self.results_model = ResultsTableModel(self.scenario_stats_df)
        self.tblResView.setModel(self.results_model)
        self.tblResView.doubleClicked.connect(self.showDetailView)
        self.tblResView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblResView.setSortingEnabled(True)
        if self.results_model.scenario_desc_col_index() is not None:
            self.tblResView.setItemDelegateForColumn(self.results_model.scenario_desc_col_index(), HtmlDelegate())
        self.tblResView.resizeColumnsToContents()
        self.tblResView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tblResViewSelect = self.tblResView.selectionModel()
        self.tblResViewSelect.selectionChanged.connect(self.btnFreqAnalysis_change_status)

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

    def openCorrTable(self):
        """
        Launches Correspondence Table Dialog
        """
        CorrespondenceTableDialog().exec_()
        RaseSettings().setIsAfterCorrespondenceTableCall(True)
        self.result_super_map, self.scenario_stats_df = calculateScenarioStats(self.sim_context_list, gui=self)
        self.results_model.reset_data(self.scenario_stats_df)

    def openWeightsTable(self):
        """
        Launches Correspondence Table Dialog
        """
        ManageWeightsDialog().exec_()
        self.result_super_map, self.scenario_stats_df = calculateScenarioStats(self.sim_context_list, gui=self)
        self.results_model.reset_data(self.scenario_stats_df)

    def handleExport(self, file_type):
        """
        Exports Results Dataframe to different formats. Includes ID Frequencies and detailed ID results
        """
        filter_str = f'{file_type.upper()} (*.{file_type})'
        path = QFileDialog.getSaveFileName(self, 'Save File', RaseSettings().getDataDirectory(), filter_str)
        if path[0]:
            export_results(self.result_super_map,
                                    self.scenario_stats_df, path[0], file_type)

    def closeSelected(self):
        """
        Closes Dialog
        """
        super().accept()

    def showDetailView(self, index):
        sim_context = self.results_model.headerData(index.row(), Qt.Vertical, Qt.UserRole)
        resultMap = self.result_super_map[sim_context]
        DetailedResultsDialog(resultMap, sim_context).exec()

    @Slot(QPoint)
    def on_tblResView_customContextMenuRequested(self, point):
        """
        Handles right click selections on the results table
        """
        index = self.tblResView.indexAt(point)
        # show the context menu only if on an a valid part of the table
        if index:
            detail_view_action = QAction(self.tr('Show Detailed Results Table'), self)
            show_freq_action = QAction(self.tr('Show Identification Results Frequency of Selected Row'
                          '{}').format("s" if len(self.tblResViewSelect.selectedRows()) > 1 else ""), self)
            menu = QMenu(self.tblResView)
            menu.addAction(detail_view_action)
            menu.addAction(show_freq_action)
            action = menu.exec_(self.tblResView.mapToGlobal(point))
            if action == show_freq_action:
                self.show_freq_results()
            elif action == detail_view_action:
                self.showDetailView(index)

    def show_freq_results(self):
        """
        Shows the frequency of all identification result strings for the selected rows in the results table
        """
        if self.tblResViewSelect.hasSelection():
            sim_context_list = [self.results_model.headerData(i.row(), Qt.Vertical, Qt.UserRole) for i
                                in self.tblResViewSelect.selectedRows()]
            freq_result_dict = compute_freq_results(self.result_super_map, sim_context_list)
            freq_result_table = FrequencyTableDialog(self, freq_result_dict)
            freq_result_table.exec()

    def btnFreqAnalysis_change_status(self):
        """
        Enables or disables the Frequency Analysis button
        """
        if self.tblResViewSelect.hasSelection():
            self.btnFreqAnalysis.setEnabled(True)
        else:
            self.btnFreqAnalysis.setEnabled(False)

    @Slot(str)
    def on_cmbXaxis_currentTextChanged(self, text):
        """
        Listens for X column change
        """
        self.show_material_cmb('X', self.cmbXaxis.currentIndex())
        for cmb in [self.cmbYaxis, self.cmbGroupBy]:
            cmb.setEnabled(True if text else False)
            if not text:
                cmb.setCurrentIndex(0)
        self.set_view_plot_btn_status()

    @Slot(str)
    def on_cmbYaxis_currentTextChanged(self, text):
        """
        Listens for Y column change
        """
        self.show_material_cmb('Y', self.cmbYaxis.currentIndex())
        self.cmbZaxis.setEnabled(True if text else False)
        if not text: self.cmbZaxis.setCurrentIndex(0)
        self.cmbGroupBy.setEnabled(True)
        self.set_view_plot_btn_status()

    @Slot(str)
    def on_cmbZaxis_currentTextChanged(self, text):
        """
        Listens for Z column change
        """
        if text:
            self.cmbGroupBy.setCurrentIndex(0)
        self.cmbGroupBy.setEnabled(False if text else True)

    def show_material_cmb(self, axis, index=None):
        """
        Shows or hides the material combo boxes based on the values of the corresponding axis combo box selected
        :param axis: 'X' or 'Y'
        """
        cmbMat = getattr(self, 'cmb' + axis + 'mat')
        txtMat = getattr(self, 'txt' + axis + 'mat')
        distanceWdg = getattr(self, 'distanceRef' + axis + 'Widget')
        txtMat.hide()
        cmbMat.hide()
        distanceWdg.hide()

        if self.comboListXY[index] in ['Source Dose', 'Source Flux', 'Distance (given dose)',
                    'Distance (given flux)', 'Background Dose', 'Background Flux']:
            cmbMat.clear()
            names = self.names_dict[self.comboListXY[index]]
            cmbMat.addItems(names)
            cmbMat.show()
            txtMat.show()
            if self.comboListXY[index] in ['Distance (given dose)', 'Distance (given flux)']:
                getattr(self, f'labelDose{axis}').setText(
                    f"with {'dose' if 'dose' in self.comboListXY[index] else 'flux'} of")
                getattr(self, f'labelDoseUnit{axis}').setText(
                    '\u00B5Sv/h at' if 'dose' in self.comboListXY[index] else '\u03B3/(cm\u00B2s) at')
                distanceWdg.show()

    @Slot(str)
    def set_view_plot_btn_status(self, t=''):
        status = True
        index_x = self.cmbXaxis.currentIndex()
        # text_x = self.cmbXaxis.currentText()
        if not index_x or (self.comboListXY[index_x].startswith('Distance (given') and not (
                        self.txtRefDoseX.hasAcceptableInput() and self.txtRefDistanceX.hasAcceptableInput())):
            status = False
        index_y = self.cmbYaxis.currentIndex()
        if self.comboListXY[index_y].startswith('Distance (given') and not (
                self.txtRefDoseY.hasAcceptableInput() and self.txtRefDistanceY.hasAcceptableInput()):
            status = False
        self.btnViewPlot.setEnabled(status)

    @Slot(bool)
    def on_btnViewPlot_clicked(self, checked):
        """
        Prepares data for plotting and launches the plotting dialog
        """
        df = self.scenario_stats_df.copy()
        unappended_titles = []
        titles = []
        ax_vars = []
        trans_ax_vars = []
        x = []
        y = []
        x_err = []
        y_err = []
        repl = []

        for axis, combolist in zip(['X', 'Y', 'Z'], [self.comboListXY, self.comboListXY, self.comboListZ]):
            cmbAxis = getattr(self, 'cmb' + axis + 'axis').currentIndex()
            matName = getattr(self, 'cmb' + axis + 'mat').currentText() if axis in ['X', 'Y'] else ''

            if combolist[cmbAxis] in ['Source Dose']:
                title = self.tr('Dose') + f' {matName}'
                unappended_title = self.tr('Dose_') + f'{matName}'
                ax_var = f'Dose_{matName}'
                trans_ax_var = self.tr('Dose') + f'_{matName}'
            elif combolist[cmbAxis] in ['Source Flux']:
                title = self.tr('Flux') + f" {matName}"
                unappended_title = self.tr('Flux_') + f'{matName}'
                ax_var = f'Flux_{matName}'
                trans_ax_var = self.tr('Flux') + f'_{matName}'
            elif combolist[cmbAxis] in ['Background Dose']:
                title = self.tr('BkgDose') + f' {matName}'
                unappended_title = self.tr('BkgDose_') + f'{matName}'
                ax_var = f'BkgDose_{matName}'
                trans_ax_var = self.tr('BkgDose') + f'_{matName}'
            elif combolist[cmbAxis] in ['Background Flux']:
                title = self.tr('BkgFlux') + f' {matName}'
                unappended_title = self.tr('BkgFlux_') + f'{matName}'
                ax_var = f'BkgFlux_{matName}'
                trans_ax_var = self.tr('BkgFlux') + f'_{matName}'
            elif combolist[cmbAxis] in ['Distance (given dose)', 'Distance (given flux)']:
                title = self.tr('Distance from {} source [cm]').format(matName)
                unappended_title = self.tr('Dose_{}').format(matName) if \
                    'dose' in combolist[cmbAxis] else self.tr('Flux_{}').format(matName)
                ax_var = f'Distance_{matName}_Dose' if 'dose' in combolist[cmbAxis] else f'Distance_{matName}_Flux'
                trans_ax_var = self.tr(f'Distance_{matName}_Dose') if 'dose' \
                    in combolist[cmbAxis] else self.tr(f'Distance_{matName}_Flux')
                txtRefDistance = getattr(self, 'txtRefDistance' + axis)
                txtRefDose = getattr(self, 'txtRefDose' + axis)
                ref_distance = float(txtRefDistance.text())
                ref_dose = float(txtRefDose.text())
                df[ax_var] = ref_distance * np.sqrt(ref_dose / df[unappended_title])  # simple 1/r^2
            else:
                title = combolist[cmbAxis]
                unappended_title = combolist[cmbAxis]
                ax_var = combolist[cmbAxis]
                trans_ax_var = combolist[cmbAxis]  # any way to translate?

            unappended_titles.append(unappended_title)
            titles.append(title)
            ax_vars.append(ax_var)
            trans_ax_vars.append(trans_ax_var)

        if len(titles) >= 3:
            for i, ax_title in enumerate(titles):
                if ax_title.startswith(self.tr('Dose')) or \
                        ax_title.startswith(self.tr('BkgDose')):
                    titles[i] = ax_title + (' (\u00B5Sv/h)')
                elif ax_title.startswith(self.tr('Flux')) or \
                        ax_title.startswith(self.tr('BkgFlux')):
                    titles[i] = ax_title + (' (\u03B3/(cm\u00B2s))')

        try:
            if self.cmbZaxis.currentText():  # 3D plotting case
                if self.cb_removezero.isChecked():
                    df_3dplot = df.loc[~((df[unappended_titles[0]] == 0) |
                             (df[unappended_titles[1]] == 0))].pivot(values=unappended_titles[2],
                                         index=unappended_titles[0], columns=unappended_titles[1])
                else:
                    df_3dplot = df.pivot(values=unappended_titles[2], index=unappended_titles[0],
                                          columns=unappended_titles[1])

                dialog = Result3DPlottingDialog(self, df_3dplot, titles)
                dialog.exec_()
            else:  # 1D and 2D plotting
                cat = self.cmbGroupBy.currentIndex()
                if cat:
                    if self.comboListGrp[cat] == 'Source Material':
                        if ax_vars[0].startswith('Distance_'):
                            categories = [s for s in df.columns.to_list() if s.startswith('Distance_')]
                        else:
                            categories = [s for s in df.columns.to_list() if s.startswith('Dose_') or s.startswith('Flux_')]
                    elif self.comboListGrp[cat] == 'Background Material':
                        categories = [s for s in df.columns.to_list() if
                                      s.startswith('BkgDose_') or s.startswith('BkgFlux_')]
                    else:
                        if len(df[self.comboListGrp[cat]].values) > 0 and type(df[self.comboListGrp[cat]].values[0]) == list:  # this is a workaround for lists of lists of influences
                            categories = list(pd.unique([', '.join(k) for k in df[self.comboListGrp[cat]].values]).tolist())
                        else:
                            categories = pd.unique(df[self.comboListGrp[cat]].values).tolist()
                else:
                    categories = [ax_vars[0]]

                for v in ['PID', 'C&C']:
                    df[f'{v}_H_err'] = (df[v] - df[f'{v}_H']).abs()
                    df[f'{v}_L_err'] = (df[v] - df[f'{v}_L']).abs()

                for cat_label in categories:
                    if isinstance(cat_label, str) and (cat_label.startswith('Dose') or cat_label.startswith('BkgDose') or
                            cat_label.startswith('Flux') or cat_label.startswith('BkgFlux') or cat_label.startswith('Distance')):
                        if cat_label.startswith('Distance'):
                            df_tmp = df.loc[df[cat_label] != float('inf')]
                        else:
                            df_tmp = df.loc[df[cat_label] != 0]
                        x.append(df_tmp[cat_label].to_list())
                    else:
                        df_tmp = df.loc[df[self.comboListGrp[cat]] == cat_label] if cat else df
                        x.append(df_tmp[ax_vars[0]].to_list())
                        if ax_vars[0] in ['PID', 'C&C']:
                            x_err.append([(l, h) for (l, h) in zip(df_tmp[f'{ax_vars[0]}_L_err'],
                                                                   df_tmp[f'{ax_vars[0]}_H_err'])])
                    repl.append(df_tmp['Repl'].tolist())
                    if ax_vars[1]:
                        y.append(df_tmp[ax_vars[1]].to_list())
                        if ax_vars[1] in ['PID', 'C&C']:
                            y_err.append([(l, h) for (l, h) in zip(df_tmp[f'{ax_vars[1]}_L_err'],
                                                                   df_tmp[f'{ax_vars[1]}_H_err'])])

                dialog = ResultPlottingDialog(self, x, y, titles, categories, repl, x_err, y_err)
                dialog.exec_()

        except Exception as e:
            traceback.print_exc()
            logging.exception(self.tr('Handled Exception'), exc_info=True)
            QMessageBox.information(self, self.tr('Info'),
                                self.tr('Sorry, the requested plot '
                                                 'cannot be generated because:\n') + str(e))
            return

    def open_help(self):
        if not self.help_dialog:
            self.help_dialog = HelpDialog(page='Use_distance.html')
        if self.help_dialog.isHidden():
            self.help_dialog.load_page(page='Use_distance.html')
            self.help_dialog.show()
        self.help_dialog.activateWindow()

    @Slot(bool)
    def on_btnSettings_clicked(self, checked):
        """
        Launches the results table settings dialog
        """
        idx = self.results_model.scenario_desc_col_index()
        dialog = ResultsTableSettings(self)
        dialog.exec_()
        self.results_model.reset_data(self.scenario_stats_df)
        if idx is not None:
            self.tblResView.setItemDelegateForColumn(idx, QStyledItemDelegate())
        if self.results_model.scenario_desc_col_index() is not None:
            self.tblResView.setItemDelegateForColumn(self.results_model.scenario_desc_col_index(), HtmlDelegate())
        self.tblResView.resizeColumnsToContents()
        self.tblResView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)


class ResultsTableSettings(QDialog):
    """Simple Dialog to allow the user to select which column to display in the results table

    The settings are stored persistently in the RaseSettings class

    :param parent: the parent dialog
    """
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.cols_list = ['Det/Replay', 'Scen Desc', 'Dose', 'Flux', 'Background Dose',
                     'Background Flux', 'Infl', 'AcqTime', 'Repl', 'Comment', 'PID', 'PID CI',
                     'PFID', 'C&C', 'C&C CI', 'TP', 'FP', 'FN', 'Precision', 'Recall', 'F_Score',
                     'wTP', 'wFP', 'wFN', 'wPrecision', 'wRecall', 'wF_Score']
        # QT treats the ampersand symbol as a special character, so it needs special treatment
        self.cb_list = [QCheckBox(self.tr(v).replace('&', '&&')) for
                        v in self.cols_list]
        layout = QVBoxLayout()
        for cb in self.cb_list:
            # if not (cb.text() == self.not_fd_mode):
            layout.addWidget(cb)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        if RaseSettings().getResultsTableSettings():
            self.set_current_settings()
        else:
            self.set_default()

    def set_default(self):
        """
        Sets default selection
        """
        for i, cb in enumerate(self.cb_list):
            if self.cols_list[i] == 'Scen Desc' or self.cols_list[i] == 'Comment':
                cb.setChecked(False)
            else:
                cb.setChecked(True)

    def set_current_settings(self):
        """
        Loads and apply the stored settings
        """
        for i, cb in enumerate(self.cb_list):
            if self.cols_list[i].replace('&&', '&') in RaseSettings().getResultsTableSettings():
                cb.setChecked(True)
            else:
                cb.setChecked(False)

    @Slot()
    def accept(self):
        """
        Stores the selected values in the RaseSettings class
        """
        selected = [self.cols_list[i].replace('&&', '&') for i, cb in enumerate(self.cb_list) if
                    cb.isChecked()]
        RaseSettings().setResultsTableSettings(selected)
        return QDialog.accept(self)


class HtmlDelegate(QStyledItemDelegate):
    '''render html text passed to the table widget item'''

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        style = option.widget.style() if option.widget else QApplication.style()

        palette = QApplication.palette()
        color = palette.highlight().color() if option.state & QStyle.State_Selected else palette.base()
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
        document.setHtml(index.model().data(index, Qt.DisplayRole))
        return QSize(document.idealWidth() + 20, fm.height())


class FrequencyTableDialog(QDialog):
    """Display a table of data from an input dictionary

    :param data: the input dictionary data
    :param parent: the parent dialog
    """
    def __init__(self, parent, data):
        QDialog.__init__(self, parent)
        self.setWindowTitle(self.tr('Results Frequency Analysis'))

        self.data = data
        self.tableWidget = QTableWidget()
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)
        self.setData()

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)

        self.widget = QWidget(self)
        self.widget.setMinimumSize(QSize(300, 300))
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.widget)
        self.ax = self.fig.add_subplot(111)
        self.navi_toolbar = NavigationToolbar(self.canvas, self.widget)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tableWidget)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.navi_toolbar)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        self.draw()

    def setData(self):
        self.tableWidget.setRowCount(len(self.data.keys()))
        self.tableWidget.setColumnCount(2)
        for n, k in enumerate(self.data.keys()):
            for col, value in enumerate([k, str(self.data[k])]):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.tableWidget.setItem(n, col, item)
        self.tableWidget.setHorizontalHeaderLabels([self.tr('Material'),
                                                    self.tr('Frequency')])

    def draw(self):
        """
        Draws the bar plot with the frequency results
        """
        self.ax.clear()
        values = [float(v) * 100 for v in self.data.values()]
        sns.barplot(x=values, y=list(self.data.keys()), ax=self.ax)
        self.ax.set_xlabel(self.tr('Frequency [%]'))
        self.ax.set_ylabel(self.tr('ID Result Label'))
        self.canvas.draw()

    def get_selected_cells_as_text(self):
        """
        Returns the selected cells of the table as plain text
        """
        selected_rows = self.tableWidget.selectedIndexes()
        text = ""
        # show the context menu only if on an a valid part of the table
        if selected_rows:
            cols = set(index.column() for index in self.tableWidget.selectedIndexes())
            for row in set(index.row() for index in self.tableWidget.selectedIndexes()):
                text += "\t".join([self.tableWidget.item(row, col).text() for col in cols])
                text += '\n'
        return text

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Copy or e.key == QKeySequence(QKeySequence.Copy) or e.key() == 67:
            QApplication.clipboard().setText(self.get_selected_cells_as_text())

    @Slot(QPoint)
    def show_context_menu(self, point):
        """
        Handles "Copy" right click selections on the table
        """
        copy_action = QAction(self.tr('Copy'), self)
        menu = QMenu(self.tableWidget)
        menu.addAction(copy_action)
        action = menu.exec_(self.tableWidget.mapToGlobal(point))
        if action == copy_action:
            QApplication.clipboard().setText(self.get_selected_cells_as_text())
