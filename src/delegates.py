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

from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QLineEdit
from src.table_def import Session, Material
from src.qt_utils import DoubleAndEmptyValidator

class OpaqueLineEditDelegate(QStyledItemDelegate):
    """
    Utility delegate to remove ghosting in line edits
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Force opaque background so the cell text underneath is not visible
        self.opaque_background(editor)
        return editor

    def opaque_background(self, editor):
        editor.setAutoFillBackground(True)
        editor.setStyleSheet("QLineEdit { background: palette(Base); }")


class DoubleOrEmptyDelegate(OpaqueLineEditDelegate):
    def __init__(self):
        OpaqueLineEditDelegate.__init__(self)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(DoubleAndEmptyValidator(bottom=0))
        self.opaque_background(editor)
        return editor


class MatSingletonComboDelegate(OpaqueLineEditDelegate):
    """
    Give combobox material name options, but do not allow for setting
    multiple rows with the same material
    """
    def __init__(self, table, matcol):
        OpaqueLineEditDelegate.__init__(self)
        self.table = table
        self.matcol = matcol

    def createEditor(self, parent, option, index):
        if index.column() == self.matcol:
            # generate list of unique material names
            materialList = sorted(set([name for material in Session().query(Material) for name in
                                       material.name_no_shielding()]))

            # remove any materials already used
            for row in range(self.table.rowCount()):
                item = self.table.item(row, self.matcol)
                if (item and item.text() in materialList) and (row != index.row()):
                    materialList.remove(item.text())

            # create and populate comboEdit
            editor = QComboBox(parent)
            editor.addItem('')
            editor.addItems(materialList)
            self.opaque_background(editor)
            return editor
        else:
            return super(MatSingletonComboDelegate, self).createEditor(parent, option, index)


