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
This module defines correct association between isotope names and
replay identification results
"""

import csv
import re

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QTableWidgetItem, QDialog, QFileDialog, \
    QMessageBox, QHeaderView, QItemDelegate, QComboBox, QMenu
from PySide6.QtGui import QAction

from src.rase_settings import RaseSettings
from .table_def import CorrespondenceTableElement, CorrespondenceTable, Session, Material
from .ui_generated import ui_correspondence_table_dialog

# Default correspondence table entries: list of (isotope, correct IDs, allowed IDs)
DEFAULT_CORRESPONDENCE_TABLE = [('Bgnd','','K40;K-40;Potassium-40;Th;Th232;Th-232;Th-232Counts;Thorium-232;Ra226;Ra-226;Radium-226;NORM;No ID;Insufficient Counts;Spt cnts > Bkg;No iso. found;Not Identified'),
                            ('Am241','Am241;Am-241;Americium-241;Am-241 (unshielded)',''),
                            ('Ba133','Ba133;Ba-133;Barium-133',''),
                            ('Cd109','Cd109;Cd-109;Cadmium-109',''),
                            ('Cf252','Cf252;Cf-252;Californium-252','Neutrons'),
                            ('Cs137','Cs137;Cs-137;Cesium-137',''),
                            ('Co57','Co57;Co-57;Cobalt-57',''),
                            ('Co60','Co60;Co-60;Cobalt-60','Annihilation;Annihilation Photons'),
                            ('Cr51','Cr51;Cr-51;Chromium-51',''),
                            ('Cu67','Cu67;Cu-67;Copper-67','Ga67;Ga-67;Gallium-67'),
                            ('DU','DU;U238;U_238;U-238;U238_DU;Uranium-238;DU-238;Uranium','LEU'),
                            ('Ga67','Ga67;Ga-67;Gallium-67','Cu67;Cu-67;Copper-67'),
                            ('HEU','HEU;U235;U_235;U-235;Uranium;Uranium-235;U risk;U-HEU;U','U_238;U-238;U238;Uranium-238;DU-238;LEU'),
                            ('I131','I131;I-131;Iodine-131',''),
                            ('K40','K40;K-40;Potassium;Potassium-40','NORM'),
                            ('LEU','LEU;U235;U-235;Uranium;Uranium-235;U risk;U','DU;HEU;U238;U-238;DU-238;Uranium-238;U-HEU'),
                            ('Lu177','Lu177;Lu-177;Lutetium-177;Lu177m;Lu-177m;Lu-177m;Lutetium-177m','Ta177;Ta-177'),
                            ('Mo99','Mo99;Mo-99;Molybdenum-99','Tc99m;Tc-99m;Tc-99;Technetium-99m'),
                            ('Na22','Na22;Na-22;Sodium-22;Beta+@Na','Annihilation;Annihilation Photons'),
                            ('Np237','Np237;Np-237;Neptunium-237',''),
                            ('Pu239','Pu239;Pu-239;WGPu;WGPu_S;WGPu-HS;Plutonium-239;Plutonium;Pu;LB Pu;MB Pu','Am241;Am-241;Americium-241;Am-241 (unshielded);Neutrons'),
                            ('Ra226','Ra226;Ra-226;Radium-226','Rn222;Rn-222;Radon-222;Radon;Po210;Po-210;Bi210;Bi-210'),
                            ('RGPu','RGPu;Pu239;Pu-239;Plutonium;Plutonium-239;Reactor Grade Plutonium;LB Pu;MB Pu;WGPu;WGPu-HS;WGPu-S','Am241;Am-241;Americium-241;Am-241 (unshielded);Neutrons;'),
                            ('Se75','Se75;Se-75;Selenium-75',''),
                            ('Sr85','Sr85;Sr-85;Strontium-85',''),
                            ('Tc99m','Tc99m;Tc-99m;Tc-99M;Technetium-99m;Tc-99','Mo99;Mo-99;Molybdenum-99'),
                            ('Tl201','Tl201;Tl-201;Thallium-201',''),
                            ('Th228','Th228;Th-228;Thorium;Thorium-228;Thorium;Th;U232;U-232;Uranium-232;U-232D;Th-232Chain','NORM;'),
                            ('Th232','Th232;Th-232;Thorium;Thorium-232;Th;Th-232Chain','Th228;Th-228;NORM'),
                            ('U232','U232;U-232;Uranium;Uranium-232;U risk;Th228;Th-228;','Th232;Th-232;Thorium'),
                            ('U233','U233;U-233;Uranium;Uranium-233;U risk','U232;U-232'),
                            ('U235','HEU;U235;U_235;U-235;Uranium;Uranium-235;U risk;U-HEU;U;','U_238;U-238;U238;Uranium-238;DU-238;LEU'),
                            ('U238','DU;U238;U_238;U-238;U238_DU;Uranium-238;DU-238','Uranium;LEU'),
                            ('WGPu','WGPu;WGPu_S;WGPu-HS;Plutonium-239;Pu-239;Pu239;Plutonium;Pu;LB Pu;MB Pu','Am241;Am-241;Americium-241;Am-241 (unshielded);Neutrons;RGPu'),
                            ('PuO2','PuO2;RGPu;WGPu;WGPu_S;WGPu-HS;Plutonium-239;Pu-239;Pu239;Plutonium;Pu;LB Pu;MB Pu','Am241;Am-241;Americium-241;Am-241 (unshielded);Neutrons')]

# translation_tag = 'corr_d'


class CorrespondenceTableDialog(ui_correspondence_table_dialog.Ui_CorrTableDialog, QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.settings = RaseSettings()
        self.NUM_COLS = 3
        self.tableEdited = False
        self.session = Session()

        # Query the entries in the current default table
        corTableRows = self.readCorrTableRows()
        if not corTableRows:
            self.NUM_ROWS = 0
        else:
            self.NUM_ROWS = corTableRows.count()

        self.tblCCCLists.setItemDelegate(Delegate(self.tblCCCLists, isotopeCol=0))
        self.tblCCCLists.setRowCount(self.NUM_ROWS)
        self.tblCCCLists.setColumnCount(self.NUM_COLS)
        self.columnLabels = [self.tr('Source'), self.tr('Correct ID'), self.tr('Allowed ID')]
        self.tblCCCLists.setHorizontalHeaderLabels(self.columnLabels)
        self.tblCCCLists.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tblCCCLists.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tblCCCLists.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tblCCCLists.customContextMenuRequested.connect(self.openMenu)
        self.tblCCCLists.setSortingEnabled(False)

        if corTableRows:
            for row, line in enumerate(corTableRows):
                self.tblCCCLists.setItem(row, 0, QTableWidgetItem(line.isotope))
                self.tblCCCLists.setItem(row, 1, QTableWidgetItem(line.corrList1))
                self.tblCCCLists.setItem(row, 2, QTableWidgetItem(line.corrList2))

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.btnAddRow.clicked.connect(self.addRow)
        self.populateDefaultComboBox()
        self.setSaveAsTableName()

        self.buttonImport.clicked.connect(self.handleImport)
        self.buttonExport.clicked.connect(self.handleExport)

        self.buttonApplyDefaultSetting.clicked.connect(self.applySettings)
        self.btnDeleteSelected.clicked.connect(self.deleteSelected)

        self.btnClose.clicked.connect(self.closeSelected)

    def closeSelected(self):
        """
        closes dialog
        """
        super().accept()

    def deleteSelected(self):
        """
        deletes selected rows
        """
        rows = self.tblCCCLists.selectionModel().selectedRows()
        indices = []
        for r in rows:
            indices.append(r.row())
        indices.sort(reverse=True)
        for index in indices:
            self.tblCCCLists.removeRow(index)
        self.NUM_ROWS = self.NUM_ROWS - len(indices)

    def setDefaultCorrTable(self, tableName):
        """
        Sets selected table as default
        """
        corrTable = self.session.query(CorrespondenceTable).filter_by(name=tableName).first()
        corrTable.is_default = True
        self.session.commit()

    def applySettings(self):
        """
        Sets selected table as default and loads it for edit
        """
        self.setDefaultCorrTable(self.setDefaultComboBox.currentText())
        self.tblCCCLists.setRowCount(0)
        if not self.readCorrTableRows():
            return
        corTableRows = self.readCorrTableRows()
        row = 0
        if corTableRows:
            for line in corTableRows:
                self.NUM_ROWS = row + 1
                self.tblCCCLists.setRowCount(self.NUM_ROWS)
                for col in range(self.NUM_COLS):
                    self.tblCCCLists.setItem(row, col, QTableWidgetItem())
                self.tblCCCLists.setItem(row, 0, QTableWidgetItem(line.isotope))
                self.tblCCCLists.setItem(row, 1, QTableWidgetItem(line.corrList1))
                self.tblCCCLists.setItem(row, 2, QTableWidgetItem(line.corrList2))
                row = row + 1
        self.setSaveAsTableName()

    def populateDefaultComboBox(self):
        """
        loads available correspondence tables into the selection box
        """
        corrTables = list(self.session.query(CorrespondenceTable))
        for i, table in enumerate(corrTables):
            self.setDefaultComboBox.addItem(table.name)
            if table.is_default:
                self.setDefaultComboBox.setCurrentIndex(i)

    def setSaveAsTableName(self):
        corrTable = self.session.query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
        if corrTable is not None:
            self.txtCorrespondenceTable.setText(corrTable.name)
            self.txtCorrespondenceTable.repaint()

    def readCorrTableRows(self):
        """
        Queries elements of the Default Correspondence Table
        :return: row elements of the correspondence table from DB
        """
        corrTable = self.session.query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
        if corrTable is None:
            return None
        else:
            return self.session.query(CorrespondenceTableElement).filter_by(
                corr_table_name=corrTable.name)

    def addRow(self):
        """
        adds row to the table in the open dialog
        """
        self.NUM_ROWS = self.NUM_ROWS + 1
        self.tblCCCLists.setRowCount(self.NUM_ROWS)
        for col in range(self.NUM_COLS):
            self.tblCCCLists.setItem(self.NUM_ROWS - 1, col, QTableWidgetItem())

    def accept(self):
        table_name = self.txtCorrespondenceTable.text()
        if table_name == "":
            QMessageBox.information(self, self.tr('Correspondence Table Name Needed'), self.tr('Please Specify New Table Name'))
            return

        self.delete_old_corr_table(self.session, table_name)

        table = self.create_corr_table(self.session, table_name)

        for row in range(self.NUM_ROWS):
            iso = self.tblCCCLists.item(row, 0).text()
            l1 = self.tblCCCLists.item(row, 1).text()
            l2 = self.tblCCCLists.item(row, 2).text()
            if iso != '':
                table = self.add_corr_table_entry(table, iso, l1, l2)
            else:
                break
        self.session.commit()
        super().accept()

    def handleExport(self):
        """
        exports to CSV
        """
        path = QFileDialog.getSaveFileName(self, self.tr('Save File'), self.settings.getDataDirectory(), 'CSV (*.csv)')
        if path[0]:
            with open(path[0], mode='w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(self.columnLabels)
                for row in range(self.tblCCCLists.rowCount()):
                    rowdata = []
                    for column in range(self.tblCCCLists.columnCount()):
                        item = self.tblCCCLists.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

    def handleImport(self):
        """
        imports from CSV
        """
        path = QFileDialog.getOpenFileName(self, self.tr('Open File'), self.settings.getDataDirectory(), 'CSV(*.csv)')
        if path[0]:
            # FIXME: This doesn't check in any way that the format of the file is correct
            with open(path[0], mode='r') as stream:
                self.tblCCCLists.setRowCount(0)
                self.tblCCCLists.setColumnCount(0)
                for rowdata in csv.reader(stream):
                    row = self.tblCCCLists.rowCount()
                    if self.tr('Correct ID') in str(rowdata):
                        continue
                    self.tblCCCLists.insertRow(row)
                    self.tblCCCLists.setColumnCount(len(rowdata))
                    for column, data in enumerate(rowdata):
                        item = QTableWidgetItem(data)
                        self.tblCCCLists.setItem(row, column, item)
            self.tblCCCLists.setHorizontalHeaderLabels(self.columnLabels)
            self.tblCCCLists.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.tblCCCLists.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.NUM_ROWS = self.tblCCCLists.rowCount()

    @Slot(QTableWidgetItem)
    def on_tblCCCLists_itemChanged(self, item):
        """
        Listener for changes to the table
        """
        self.tableEdited = True

    def openMenu(self, point):
        """
        Adds sorting to the table
        """
        sortAction = QAction('Sort', self)
        menu = QMenu(self.tblCCCLists)
        menu.addAction(sortAction)
        action = menu.exec_(self.tblCCCLists.mapToGlobal(point))
        if action == sortAction:
            sortingCol = self.tblCCCLists.currentColumn()
            sortingList = []
            rowMap = {}
            for row in range(self.NUM_ROWS):
                if self.tblCCCLists.item(row, 0).text() == "":
                    continue
                rowMapItem = {}
                for col in range(self.NUM_COLS):
                    if col != sortingCol:
                        rowMapItem[col] = self.tblCCCLists.item(row, col).text()
                rowMap[self.tblCCCLists.item(row, sortingCol).text()] = rowMapItem
                sortingList.append(self.tblCCCLists.item(row, sortingCol).text())
            sortingList.sort()
            row = 0
            for token in sortingList:
                rowMapItem = rowMap[token]
                for col in rowMapItem:
                    self.tblCCCLists.setItem(row, col, QTableWidgetItem(rowMapItem[col]))
                self.tblCCCLists.setItem(row, sortingCol, QTableWidgetItem(token))
                row = row + 1

    @staticmethod
    def delete_old_corr_table(session, table_name):
        corrTable = session.query(CorrespondenceTable).filter_by(name=table_name).one_or_none()
        if corrTable is not None:
            # table already exists, so delete first before overwriting
            session.query(CorrespondenceTableElement).filter_by(corr_table_name=table_name).delete()
            session.delete(corrTable)
            session.commit()

    @staticmethod
    def create_corr_table(session, table_name):
        table = CorrespondenceTable(name=table_name, is_default=True)
        session.add(table)
        return table

    @staticmethod
    def add_corr_table_entry(table, iso, l1='', l2=''):
        corrTsbleEntry = CorrespondenceTableElement(isotope=iso, table=table, corrList1=l1,
                                                    corrList2=l2)
        Session().add(corrTsbleEntry)
        return table


class Delegate(QItemDelegate):
    def __init__(self, tblCorr, isotopeCol, editable=False):
        QItemDelegate.__init__(self)
        self.tblCorr = tblCorr
        self.isotopeCol = isotopeCol
        self.editable = editable

    def createEditor(self, parent, option, index):
        if index.column() == self.isotopeCol:
            # generate list of unique material names
            materialList = sorted(set([name for material in Session().query(Material) for name in
                                       material.name_no_shielding()]))

            # remove any materials already used
            for row in range(self.tblCorr.rowCount()):
                item = self.tblCorr.item(row, self.isotopeCol)
                if item and item.text() in materialList:
                    materialList.remove(item.text())

            # create and populate comboEdit
            comboEdit = QComboBox(parent)
            comboEdit.setEditable(self.editable)
            comboEdit.addItem('')
            comboEdit.addItems(materialList)
            return comboEdit
        else:
            return super(Delegate, self).createEditor(parent, option, index)


class CorrespondenceData:
    def __init__(self, gui=None):
        self.gui = gui
        self.corrHash = {}
        self.settings = RaseSettings()

    def getCorrHash(self):
        """
        Reads the Correspondence Table and creates
        association of isotopes to correct and allowed ids
        :return: association of isotopes to correct and allowed ids
        """
        corrTable = Session().query(CorrespondenceTable).filter_by(is_default=True).one_or_none()
        if not corrTable and self.gui is not None:
            QMessageBox.critical(self.gui, self.tr('Set Correspondence Table'), self.tr('Must specify a Correspondence Table'))
            return
        # if the corrHash dict has already been populated and the Correspondence Table Dialog has not
        # been called since it was populated, there is no need to re-populate it
        if self.corrHash and not self.settings.getIsAfterCorrespondenceTableCall():
            return self.corrHash
        self.corrHash = {}
        self.settings.setIsAfterCorrespondenceTableCall(False)
        corTableRows = (
            Session().query(CorrespondenceTableElement).filter_by(corr_table_name=corrTable.name))
        for line in corTableRows:
            isotope = line.isotope.strip()
            # correct_ids is a list of ";" delimited strings
            correct_ids = [l.strip() for l in line.corrList1.split(';') if l.strip()]
            # allowed_ids is a single ";" delimited string
            allowed_ids = [l.strip() for l in line.corrList2.split(';') if l.strip()]
            self.corrHash[isotope] = [correct_ids, allowed_ids]
        return self.corrHash

    def getCorrTableData(self, scenarioIsotopes, backgroundIsotopes):
        allowed_list = []
        correct_list = []
        # store source and background isotopes together with source/background info
        isoPairList = []
        for iso in scenarioIsotopes:
            isoPairList.append((iso, "source"))
        for iso in backgroundIsotopes:
            isoPairList.append((iso, "background"))
        for isoP in isoPairList:
            iso = isoP[0]
            if isoP[1] == "source":
                isSource = True
            else:
                isSource = False
            # get the correspondence table entry for this isotope
            # or use default names if nothing is specified
            # print("iso="+iso)
            isohash = self.getCorrHash()
            if iso not in isohash:
                if isSource:
                    tmp = re.split('(\d+)', iso)  # split by numbers
                    correct_ids = [iso, tmp[0] + '-' + ''.join(tmp[1:])]  # e.g. Am241 and Am-241
                    allowed_ids = []
                else:
                    correct_ids = []
                    allowed_ids = []
            else:
                correct_ids, allowed_ids = isohash[iso]
            # Build the list of all allowed isotopes
            allowed_list += allowed_ids
            correct_list.append(correct_ids)

        return [i[0] for i in isoPairList], correct_list, allowed_list

def set_default_corrtable():
    session = Session()
    # only populate if no default table set
    if session.query(CorrespondenceTable).filter_by(is_default=True).first() is None:
        table = CorrespondenceTable(name='default', is_default=True)
        session.add(table)
        for iso, corr1, corr2 in DEFAULT_CORRESPONDENCE_TABLE:
            elem = CorrespondenceTableElement(isotope=iso, table=table,
                                              corrList1=corr1, corrList2=corr2)
            session.add(elem)
        session.commit()