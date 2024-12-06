from itertools import product

import pytest

from src.contexts import SimContext
from src.rase_settings import RaseSettings
import os
from src.rase_functions import *
from sqlalchemy.orm import close_all_sessions

import sys
from time import sleep

import pytest
from src.rase import Rase
from PySide6.QtCore import QObject, Signal


from src.correspondence_table_dialog import CorrespondenceTableDialog as ctd
from src.detector_dialog import DetectorDialog

from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.scenario_group_dialog import GroupSettings as gsd
from src.table_def import ScenarioGroup, Replay, CorrespondenceTable
from sqlalchemy.orm import close_all_sessions
from pathlib import Path

@pytest.fixture(scope='session', autouse=True)
def temp_data_dir():
    """Make sure no sample spectra are left after the final test is run"""
    settings = RaseSettings()
    original_data_dir = settings.getDataDirectory()
    settings.setDataDirectory(os.path.join(os.getcwd(),'__temp_test_rase'))
    yield settings.getDataDirectory()  # anything before this line will be run prior to the tests
    settings = RaseSettings()
    settings.setDataDirectory(original_data_dir)

@pytest.fixture(scope="class", autouse=True)
def db_and_output_folder():
    settings = RaseSettings()
    close_all_sessions()
    if Session.bind:
        Session.bind.dispose()
    """Delete and recreate the database between test classes"""
    if os.path.isdir(settings.getSampleDirectory()):
        shutil.rmtree(settings.getSampleDirectory())
        print(f'Deleting sample dir at {settings.getSampleDirectory()}')
    if os.path.isfile(settings.getDatabaseFilepath()):
        os.remove(settings.getDatabaseFilepath())
        print(f'Deleting DB at {settings.getDatabaseFilepath()}')
    if os.path.isdir(Path(settings.getDataDirectory())/'gadras_injections'):
        shutil.rmtree(Path(settings.getDataDirectory())/'gadras_injections')
        print(f'Deleting gadras pcfs at {Path(settings.getDataDirectory())/"gadras_injections"}')
    if os.path.isdir(Path(settings.getDataDirectory())/'converted_gadras'):
        shutil.rmtree(Path(settings.getDataDirectory())/'converted_gadras')
        print(f'Deleting gadras N42s at {Path(settings.getDataDirectory())/"converted_gadras"}')
    settings = RaseSettings()
    close_all_sessions()
    dataDir = settings.getDataDirectory()

    os.makedirs(dataDir, exist_ok=True)
    initializeDatabase(settings.getDatabaseFilepath())
    yield
    close_all_sessions()

@pytest.fixture(scope="session",)
def dummy_base_spectrum():
    dummy_dir = Path(__file__).parent/'..'/'baseSpectra'/ 'DummySpectra'
    assert dummy_dir.is_dir()
    assert (dummy_dir/'DUMMY_M001_Delta_Delta.n42').is_file()
    return str(dummy_dir.resolve())

@pytest.fixture(scope="session",)
def generic_nai_spectra():
    dummy_dir = Path(__file__).parent/'..'/'baseSpectra'/'genericNaI'
    assert dummy_dir.is_dir()
    assert (dummy_dir/'Cs137,n42').is_file()
    return str(dummy_dir.resolve())

class Helper(QObject):
    finished = Signal()


class HelpObjectCreation:
    def __init__(self):
        self.default_correspondence_table = [('Bgnd','','K40;K-40;Potassium-40;Th;Th232;Th-232;Th-232Counts;Thorium-232;Ra226;Ra-226;Radium-226;NORM;No ID;Insufficient Counts;Spt cnts > Bkg;No iso. found;Not Identified'),
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


    def get_default_detector_name(self):
        return 'test_detector'

    def get_default_replay_name(self):
        return 'dummy_replay'

    def get_default_channels(self):
        return ','.join(['1' for _ in range(1024)])

    def get_default_channel_count(self):
        return 1024

    def get_default_scen_pars(self):
        acq_times = self.get_default_acq_times()
        replications = self.get_default_replications()
        fd_mode, fd_mode_back = self.get_default_fd_modes()
        mat_names, back_names = self.get_default_mat_names()
        doses, doses_back = self.get_default_doses()

        return acq_times, replications, fd_mode, fd_mode_back, mat_names, back_names, doses, doses_back

    def get_default_acq_times(self):
        return [60, 20]

    def get_default_replications(self):
        return [3, 3]

    def get_default_fd_modes(self):
        return [['DOSE'], ['FLUX', 'DOSE']], [['DOSE'], ['DOSE']]

    def get_default_mat_names(self):
        return [['Cs137'], ['dummy_mat_2', 'dummy_mat_3']], [['dummy_back_1'], ['dummy_back_2']]

    def get_default_ecal(self):
        return [[[0,1,0,0]] , [[0,1,0,0],[0,2,0,0]] ], [[[0,1,0,0]],[[0,3,0,0]]]

    def get_default_doses(self):
        return [[.31], [2.3, 1.1]], [[.08], [.077]]

    def get_default_rt_lt(self):
        return [[[1200.0, 1189.2]], [[1200.0, 1164.2], [1200.0, 1199.2]]], [[[3600.0, 3598.2]], [[3600.0, 3573.1]]]

    def get_default_sensitivities(self):
        return [[10000], [300, 400]], [[2300], [2100]]

    def get_default_base_counts(self):
        n_ch = self.get_default_channel_count()
        templist = []
        for n in [2367, 469, 381, 1213, 1107]:
            temparr = np.array([n] * n_ch)
            tempcounts = [str(a) for a in temparr[:-1]] + [str(temparr[-1])]
            templist.append(', '.join(tempcounts))
        return [[templist[0]], [templist[1], templist[2]]], [[templist[3]], [templist[4]]]

    def get_scengroups(self, session):
        group_name = 'group_name'
        if session.query(ScenarioGroup).filter_by(name=group_name).first():
            return [session.query(ScenarioGroup).filter_by(name=group_name).first()]

        gsd.add_groups(session, group_name)
        assert session.query(ScenarioGroup).filter_by(name=group_name).first()
        return [session.query(ScenarioGroup).filter_by(name=group_name).first()]

    def create_base_materials(self, fd_mode, fd_mode_back, mat_names, back_names, doses, doses_back):
        session = Session()

        for a, f in zip([mat_names, back_names], [get_or_create_material, get_or_create_material]):
            for s in a:
                for m in s:
                    assert f(session, m)

        mat_dose_arr = [[m, d, f] for m, d, f in zip(fd_mode, mat_names, doses)]
        back_dose_arr = [[m, d, f] for m, d, f in zip(fd_mode_back, back_names, doses_back)]

        scens = []
        bscens = []
        for scenlists, m_arr, func in zip([scens, bscens],
                                          [mat_dose_arr, back_dose_arr],
                                          [get_or_create_material, get_or_create_material]):
            for m in m_arr:
                slist = []
                for a, b, c in zip(*m):
                    slist.append((a, func(session, b), c))
                scenlists.append(slist)

        scenMaterials = []
        bcgkScenMaterials = []
        for scen in scens:
            scenMaterials.append([ScenarioMaterial(material=m, dose=float(d), fd_mode=u) for u, m, d in scen])
        for bscen in bscens:
            bcgkScenMaterials.append([ScenarioBackgroundMaterial(material=m, dose=float(d), fd_mode=u)
                                      for u, m, d in bscen])

        return scenMaterials, bcgkScenMaterials

    def add_default_scens(self):
        acq_times, replications, fd_mode, fd_mode_back, mat_names, back_names, doses, doses_back = self.get_default_scen_pars()
        session = Session()

        scenMaterials, bcgkScenMaterials = self.create_base_materials(fd_mode, fd_mode_back, mat_names, back_names,
                                                                    doses, doses_back)
        for acqTime, replication, baseSpectrum, backSpectrum in zip(acq_times, replications, scenMaterials, bcgkScenMaterials):
            scen_hash = Scenario.scenario_hash(float(acqTime), baseSpectrum, backSpectrum, [])
            if not session.query(Scenario).filter_by(id=scen_hash).first():
                session.add(Scenario(float(acqTime), replication, baseSpectrum, backSpectrum, [], self.get_scengroups(session)))
        return

    def create_empty_detector(self):
        detector_name = self.get_default_detector_name()
        session = Session()
        d_dialog = DetectorDialog(None)
        if session.query(Detector).filter_by(name=detector_name).first():
            delete_instrument(session, detector_name)
        d_dialog.detector = Detector(name=detector_name)
        session.add(d_dialog.detector)

    def add_default_base_spectra(self):
        session = Session()
        baseSpectra = []
        mat_names, back_names = self.get_default_mat_names()
        fg_rt_lt, bg_rt_lt = self.get_default_rt_lt()
        fg_fds, bg_fds = self.get_default_fd_modes()
        fg_sens, bg_sens = self.get_default_sensitivities()
        fg_bscounts, bg_bscounts = self.get_default_base_counts()
        fg_ecals, bg_ecals = self.get_default_ecal()


        for mats, real_live_times, fd_modes, sensitivities, bscounts, ecals in zip(mat_names + back_names,
                                                                        fg_rt_lt + bg_rt_lt, fg_fds + bg_fds,
                                                                        fg_sens + bg_sens, fg_bscounts + bg_bscounts,
                                                                            fg_ecals+bg_ecals):
            for m, r_l_t, fd, sens, cnts, ecal in zip(mats, real_live_times, fd_modes, sensitivities, bscounts, ecals):
                if fd == 'DOSE':
                    rase_sensitivity = sens
                    flux_sensitivity = None
                else:
                    rase_sensitivity = None
                    flux_sensitivity = sens

                baseSpectra.append(BaseSpectrum(material=get_or_create_material(session, m),
                                                filename='.', realtime=r_l_t[0], livetime=r_l_t[1],
                                                rase_sensitivity=rase_sensitivity, flux_sensitivity=flux_sensitivity,
                                                baseCounts=cnts, ecal=ecal))

        return baseSpectra

    def get_default_detector_params(self):
        chan_count = self.get_default_channels()
        ecal0 = 0.1
        ecal1 = 1
        ecal2 = 0.0000001
        ecal3 = 0

        manufacturer = 'manufacturer'
        instr_id = 'instr_id'
        class_code = 'class_code'
        hardware_version = 'hardware_version'
        resultsTranslator = None
        replays = []

        ecal = [ecal0, ecal1, ecal2, ecal3]
        params = [manufacturer, instr_id, class_code, hardware_version, replays, resultsTranslator]

        return chan_count, ecal, params

    def set_default_detector_params(self):
        chan_counts, ecal, params = self.get_default_detector_params()
        d_dialog = DetectorDialog(None, self.get_default_detector_name())
        d_dialog.model.set_chan_count_from_spectrum(chan_counts)
        d_dialog.model.set_ecal(ecal)
        d_dialog.model.set_detector_params(*params)

    def create_default_replay(self):
        session = Session()
        name = self.get_default_replay_name()
        exe_path = f"{Path(__file__).parent / '../tools/fixed_replay.py'}"
        is_cmd_line = True
        settings = "INPUTDIR OUTPUTDIR"
        n42_template_path = None
        input_filename_suffix = '.n42'

        replay_db = session.query(Replay).filter_by(name=name).one_or_none()
        if replay_db:
            return replay_db

        replay = Replay()
        replay.name = name
        replay.exe_path = exe_path
        replay.is_cmd_line = is_cmd_line
        replay.settings = settings
        replay.n42_template_path = n42_template_path
        replay.input_filename_suffix = input_filename_suffix
        session.add(replay)
        return replay

    def add_default_replay(self):
        session = Session()
        detector = session.query(Detector).filter_by(name=self.get_default_detector_name()).first()
        replay = session.query(Replay).filter_by(name=self.get_default_replay_name()).first()
        detector.add_replay(replay)

    def create_default_detector_scen(self):
        session = Session()

        self.add_default_scens()
        self.create_empty_detector()
        baseSpectra = self.add_default_base_spectra()

        detector = session.query(Detector).filter_by(name=self.get_default_detector_name()).first()
        for bs in baseSpectra:
            detector.base_spectra.append(bs)
        self.set_default_detector_params()
        self.create_default_replay()
        self.add_default_replay()
        session.commit()

    def create_default_corr_table(self):
        session = Session()
        table_name = 'default_table'
        iso = 'Bgnd'

        if session.query(CorrespondenceTable).filter_by(name='default_table').first() is None:
            table = ctd.create_corr_table(session, table_name)
            ctd.add_corr_table_entry(table, iso)
            session.commit()

    def create_filled_corr_table(self):
        """TODO: remove this later once we code in a way to import corr tables"""
        session = Session()
        table_name = 'default_table'
        corrtable_tuples = self.default_correspondence_table.copy()
        if session.query(CorrespondenceTable).filter_by(name='default_table').first() is None:
            table = ctd.create_corr_table(session, table_name)
            for t in corrtable_tuples:
                ctd.add_corr_table_entry(table, t[0], t[1], t[2])
            session.commit()

    def delete_corr_table(self, table_name=None):
        session = Session()
        if table_name:
            ctd.delete_old_corr_table(session, table_name)

    def create_default_workflow(self):
        self.create_default_detector_scen()
        self.create_default_corr_table()

    def get_default_workflow(self):
        session = Session()
        detectors = [d for d in session.query(Detector).filter_by(name=self.get_default_detector_name()).all()]
        assert detectors
        replays = [r for d in detectors for r in d.replays]
        assert replays
        scenarios = [scen for scen in session.query(Scenario).all()]
        assert scenarios
        return [SimContext(detector=d, replay=r, scenario=s) for (d, r), s in product(zip(detectors, replays), scenarios)]

# class HelpGenericCreation:
#     def __init__(self):
#         session = Session()
#         bscmodel = BaseSpectraLoadModel()
#         bscmodel.get_spectra_data(generic_nai_spectra)
#         bscmodel.accept()
#         dmodel = DetectorModel('test_from_basespectra')
#         dmodel.assign_spectra(bscmodel)

#         dets, scens = self.get_default_workflow_objects()
#         det_names = [d.name for d in dets]
#         assert det_names
#         scen_ids = [scen.id for scen in scens]
#         assert scen_ids
#         return det_names, scen_ids
#
    def get_default_workflow_objects(self):
        session = Session()
        dets = session.query(Detector).filter_by(name=self.get_default_detector_name()).order_by(Detector.name.desc()).all()
        assert dets
        scens = session.query(Scenario).order_by(Scenario.id.desc()).all()
        assert scens
        return dets, scens
#
@pytest.fixture(scope='session')
def main_window():
    w = Rase(None)
    return w

@pytest.fixture(scope='class')
def filled_db():
    hoc = HelpObjectCreation()
    hoc.create_default_workflow()
    return hoc