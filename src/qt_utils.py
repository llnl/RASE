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
import locale
import platform

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, QEventLoop, Slot, QObject, Signal, QAbstractListModel, QCoreApplication, QLibraryInfo, \
    QTranslator
from PySide6.QtWidgets import QApplication

from src.table_def import Session, Detector


class QSignalWait(QObject):
    """
    Class that waits for a QTSignal and returns its value
    Works only with signals with no type or type int,str,bool
    """
    def __init__(self, signal, parent=None):
        super(QSignalWait, self).__init__(parent)
        self.state = None
        self.signal = signal
        self.loop = QEventLoop()

    @Slot()
    @Slot(bool)
    @Slot(str)
    @Slot(int)
    def _quit(self, state = None):
        self.state = state
        self.loop.quit()

    def wait(self):
        """Waits for a signal to be emitted.
        """
        self.signal.connect(self._quit)
        self.loop.exec()
        self.signal.disconnect(self._quit)
        return self.state


class DoubleValidator(QtGui.QDoubleValidator):
    '''Reimplements QDoubleValidator with signal when validation changes'''
    validationChanged = Signal(QtGui.QValidator.State)

    def validate(self, input, pos):
        state, input, pos = super().validate(input, pos)
        self.validationChanged.emit(state)
        return state, input, pos


class DoubleValidatorInfinity(QtGui.QDoubleValidator):
    '''
    Reimplements QDoubleValidator with signal when validation changes
    and accepts '+inf' and '-inf' values
    '''
    validationChanged = Signal(QtGui.QValidator.State)

    def validate(self, input, pos):
        state, input, pos = super().validate(input, pos)
        if input == 'i' or input == 'in' or input == '-i' or input == '-in':
            state = QtGui.QValidator.Intermediate
        if input == 'inf' or input == '-inf':
            state = QtGui.QValidator.Acceptable
        self.validationChanged.emit(state)
        return state, input, pos


class IntValidator(QtGui.QIntValidator):
    '''Reimplements QIntValidator with signal when validation changes'''
    validationChanged = Signal(QtGui.QValidator.State)

    def validate(self, input, pos):
        state, input, pos = super().validate(input, pos)
        self.validationChanged.emit(state)
        return state, input, pos


class RegExpValidator(QtGui.QRegularExpressionValidator):
    """Reimplements QRegularExpressionValidator with signal when validation changes"""
    validationChanged = Signal(QtGui.QValidator.State)

    def validate(self, input, pos):
        state, input, pos = super().validate(input, pos)
        self.validationChanged.emit(state)
        return state, input, pos


class DoubleAndEmptyValidator(QtGui.QDoubleValidator):
    """
    Validate double values or empty string.
    """

    def validate(self, inputText, pos):
        """
        Reimplemented from `QDoubleValidator.validate`.
        Allow to provide an empty value.
        :param str inputText: Text to validate
        :param int pos: Position of the cursor
        """
        if inputText.strip() == "":
            # python API is not the same as C++ one
            return QtGui.QValidator.Acceptable, inputText, pos
        return super(DoubleAndEmptyValidator, self).validate(inputText, pos)

    def toValue(self, text):
        """Convert the input string into an interpreted value
        :param str text: Input string
        :rtype: Tuple[object,bool]
        :returns: A tuple containing the resulting object and True if the
            string is valid
        """
        if text.strip() == "":
            return None, True
        value, validated = self.locale().toDouble(text)
        return value, validated

    def toText(self, value):
        """Convert the input string into an interpreted value
        :param object value: Input object
        :rtype: str
        """
        if value is None:
            return ""
        return str(value)



class BaseSpectraListModel(QAbstractListModel):

    def __init__(self, data=None,  *args, **kwargs):
        super(BaseSpectraListModel, self).__init__(*args, **kwargs)
        self.bs_list = data or []

    def reset_data(self):
        """
        Dump old spectra table
        """
        self.layoutAboutToBeChanged.emit()
        self.bs_list.clear()
        self.layoutChanged.emit()

    def add_spectra(self, base_spectra):
        self.layoutAboutToBeChanged.emit()
        self.bs_list = sorted([baseSpectrum.material.name for baseSpectrum in base_spectra], key=lambda s: s.lower())
        self.layoutChanged.emit()

    def update_fromdetector(self, detector_name=''):
        self.reset_data()
        if detector_name != '':
            session = Session()
            det = session.query(Detector).filter_by(name=detector_name).first()
            self.add_spectra(det.base_spectra)

    def rowCount(self, index=None):
        return len(self.bs_list)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.bs_list[index.row()]

class Translatable:
    @classmethod
    def tr(cls, text: str) -> str:
        return QCoreApplication.translate(cls.__name__, text)

def get_lang():
    # Apparently there is a bug in Qt QLocale.system() function, so I'm using a workaround to get the language
    if platform.system() == 'Windows':
        import ctypes
        windll = ctypes.windll.kernel32
        return locale.windows_locale[windll.GetUserDefaultUILanguage()]
    else:
        return locale.getdefaultlocale()[0]

def qt_install_translator():
    app = QApplication.instance()

    lang = get_lang()

    path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    translator = QTranslator(app)
    if translator.load(f'qtbase_{lang}', path):
        app.installTranslator(translator)

    translator = QTranslator(app)
    # This would be the correct implementation if QLocale().system() worked on Mac
    # if translator.load(QLocale().system(), 'rase', '_', tr_path, '.qm'):
    #     app.installTranslator(translator)
    # attempt to load from subfolder of current or parent folder (useful e.g. when running tests)
    if translator.load(f'rase_{lang}', './translations') or translator.load(f'rase_{lang}', '../translations'):
        app.installTranslator(translator)

    return lang