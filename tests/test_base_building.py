import sys
from time import sleep

import pytest
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QDialogButtonBox, QMenu, QApplication, QMessageBox, QDialog, QTableWidgetItem

from src.correspondence_table_dialog import CorrespondenceTableDialog as ctd
from src.detector_dialog import DetectorDialog, DetectorModel
from src.replay_dialog import ReplayModel
from src.rase import Rase, SampleSpectraGenerationGUI, ReplayGenerationGUI
from src.rase_functions import *
from src.create_base_spectra_dialog import CreateBaseSpectraDialog
from src import base_building_algos as bb
# from src.create_shielded_spectra_dialog import ShieldingModule
# pytest.main(['-s'])
from .fixtures import (temp_data_dir, db_and_output_folder, generic_nai_spectra, dummy_base_spectrum,
                       HelpObjectCreation, Helper)
from itertools import product
from pathlib import Path
import yaml


examplepath = Path(__file__).parent.parent/'baseSpectra/genericNaI'
templatepath = Path(__file__).parent.parent/'n42Templates/Symetrica_SL23N_template.n42'


@pytest.fixture(scope='session')
def basefolder(temp_data_dir):
    folder = Path(temp_data_dir) / 'base_spectra'
    folder.mkdir(exist_ok=True)
    return folder

@pytest.fixture(scope='session')
def baseconfig():
    configpath = Path(__file__).parent.parent / 'configs/base_spectra_config.yaml'
    with open(configpath, mode='r') as file:
        config = yaml.safe_load(file)
    return config
class Test_Base_Building:

    def test_basic(self,basefolder):
        bb.do_glob(str(examplepath/'*Am241.n42'), config = bb.default_config['rase n42'], outputfolder=basefolder, manufacturer='Generic', model='NaI2x2', source='Am241', subtraction=None,
           uSievertsph=1, fluxValue=None,)

    def test_sum_files(self,basefolder):
        bb.do_glob(str(examplepath/'*.n42'), config = bb.default_config['rase n42'], outputfolder=basefolder, manufacturer='Generic', model='NaI2x2', source='Am241', subtraction=None,
           uSievertsph=1, fluxValue=None,)

    def test_subtraction(self, basefolder):
        bb.do_glob(str(examplepath / '*Co60.n42'), config=bb.default_config['rase n42'], outputfolder=basefolder,
                   manufacturer='Generic', model='NaI2x2', source='Co60', subtraction=str(examplepath /'VGeneric_MNaI2x2_Bgnd.n42'), subtraction_config=bb.default_config['rase n42'],
                   uSievertsph=1, fluxValue=None, )

    def test_GUI(self, qtbot,basefolder):
        from src.create_base_spectra_dialog import ColNum
        d = CreateBaseSpectraDialog(None)
        d.checkBox_ComboFolder.setChecked(True)

        example = Path(__file__).parent / 'example_raw/example_1'
        d.on_btnLoadSources_clicked(None, str(example))
        d.txtModelID.setText('exampleModel')
        d.txtVendorID.setText('exampleVendor')
        d.txtOutFolder.setText(str(basefolder))

        table = d.createBSTable.sourceTable
        for row in range(table.rowCount()):
            matItem = QTableWidgetItem(f'mat{row}')
            table.setItem(row,ColNum.matID,matItem)
            doseItem = QTableWidgetItem('1')
            table.setItem(row, ColNum.dose, doseItem)
        assert d.buttonBox.button(QDialogButtonBox.Ok).isEnabled()
        d.accept()

    def test_multi_volume(self,basefolder,baseconfig):
        example = Path(__file__).parent / 'example_raw/example_2/Bgnd_Static'

        bb.do_glob(str(example/'*E0088.n42'), config = baseconfig['BTI X5600'], outputfolder=basefolder, manufacturer='multivol', model='bti-style', source='Example', subtraction=None,
           uSievertsph=1, fluxValue=None,)

    def test_retemplate(self,basefolder):
        from mako.template import Template

        inputfile = examplepath/'VGeneric_MNaI2x2_Am241.n42'
        config = bb.default_config['rase n42']

        ET = get_ET_from_file(str(inputfile))

        fake_secondary_dict = {'Background_FAKE':
            {'spectrum': config['measurement_spectrum_xpath'],
            'livetime': config['livetime_xpath'],
            'realtime': config['realtime_xpath'],
            'classcode':'FAKE'}
        }

        values = bb.get_ET_values(ET=ET, measureXPath=config['measurement_spectrum_xpath'],
                               realtimeXPath=config['realtime_xpath'], livetimeXPath=config['livetime_xpath'],
                               calibration=config['calibration'],
                               additionals=config.get('additionals'), secondaries_dict=fake_secondary_dict,
                               uSievertsph=1)

        template = Template(filename=str(templatepath), input_encoding='utf-8', strict_undefined=True)

        output = bb.build_base_ET(rawValues=values, device_template= template)
        outputfilename = f'templated_{inputfile.name}'
        bb.write_base_text(output, basefolder, outputfilename)


