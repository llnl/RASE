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
from src.correspondence_table_dialog import DEFAULT_CORRESPONDENCE_TABLE

from src.detector_dialog import DetectorModel

from src.rase_functions import *
from src.rase_settings import RaseSettings
from src.scenario_group_dialog import GroupSettings as gsd
from src.table_def import ScenarioGroup, Replay, CorrespondenceTable
from sqlalchemy.orm import close_all_sessions
from pathlib import Path


def cleanup():
    """Delete and recreate the database between test classes"""
    close_all_sessions()
    try:
        if Session.bind:
            Session.bind.dispose()
    except NameError:
        pass
    settings = RaseSettings()
    # remove sampled spectra dir if present
    if os.path.isdir(settings.getSampleDirectory()):
        shutil.rmtree(settings.getSampleDirectory(), ignore_errors=True)
        print(f'Deleting sample dir at {settings.getSampleDirectory()}')
    if os.path.isfile(settings.getDatabaseFilepath()):
        os.remove(settings.getDatabaseFilepath())
        print(f'Deleting DB at {settings.getDatabaseFilepath()}')
    if os.path.isdir(Path(settings.getDataDirectory())/'gadras_injections'):
        shutil.rmtree(Path(settings.getDataDirectory())/'gadras_injections', ignore_errors=True)
        print(f'Deleting gadras pcfs at {Path(settings.getDataDirectory())/'gadras_injections'}')
    if os.path.isdir(Path(settings.getDataDirectory())/'converted_gadras'):
        shutil.rmtree(Path(settings.getDataDirectory())/'converted_gadras', ignore_errors=True)
        print(f'Deleting gadras N42s at {Path(settings.getDataDirectory())/'converted_gadras'}')
    # If using the temporary test data directory, remove it entirely
    data_dir = Path(settings.getDataDirectory())
    if data_dir.name == '__temp_test_rase' and data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)


@pytest.fixture(scope='session', autouse=True)
def temp_data_dir():
    """Make sure no sample spectra are left after the final test is run"""
    settings = RaseSettings()
    original_data_dir = settings.getDataDirectory()
    settings.setDataDirectory(os.path.join(os.getcwd(),'__temp_test_rase'))
    yield settings.getDataDirectory()  # anything before this line will be run prior to the tests
    settings = RaseSettings()
    settings.setDataDirectory(original_data_dir)
    # Best-effort removal of the temp directory at end of session
    temp_dir = Path(os.path.join(os.getcwd(),'__temp_test_rase'))
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="class", autouse=True)
def db_and_output_folder():
    close_all_sessions()
    if Session.bind:
        Session.bind.dispose()
    cleanup()
    settings = RaseSettings()
    close_all_sessions()
    settings.ensureDataDirectories()
    initializeDatabase(settings.getDatabaseFilepath())
    yield
    close_all_sessions()
    cleanup()
    # Repeat deletion logic here if you want to clean up after the class

@pytest.fixture(scope="session",)
def dummy_base_spectrum():
    dummy_dir = Path(__file__).parent.parent /'baseSpectra'/ 'DummySpectra'
    assert dummy_dir.is_dir()
    assert (dummy_dir/'DUMMY_M001_Delta_Delta.n42').is_file()
    return str(dummy_dir.resolve())

@pytest.fixture(scope="session",)
def generic_nai_spectra():
    dummy_dir = Path(__file__).parent.parent /'baseSpectra'/ 'genericNaI'
    assert dummy_dir.is_dir()
    assert (dummy_dir/'VGeneric_MNaI2x2_Cs137.n42').is_file()
    return str(dummy_dir.resolve())

@pytest.fixture(scope="session",)
def example_multisec_base():
    dummy_dir = Path(__file__).parent/'example_base'/'multisec'
    assert dummy_dir.is_dir()
    assert (dummy_dir/'VTest_MTest_Co60_multisec.n42').is_file()
    return str(dummy_dir.resolve())



class Helper(QObject):
    finished = Signal()


class HelpObjectCreation:
    def __init__(self):
        self.default_correspondence_table = DEFAULT_CORRESPONDENCE_TABLE.copy()

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
        if session.query(Detector).filter_by(name=detector_name).first():
            delete_instrument(session, detector_name)
        model = DetectorModel(detector_name)
        model.accept()

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
        model = DetectorModel(self.get_default_detector_name())
        # d_dialog = DetectorDialog(None, self.get_default_detector_name())
        model.set_chan_count_from_spectrum(chan_counts)
        model.set_ecal(ecal)
        model.set_detector_params(*params)
        model.accept()

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


@pytest.fixture(scope='session')
def main_window():
    w = Rase(None)
    return w

@pytest.fixture(scope='class')
def filled_db():
    hoc = HelpObjectCreation()
    hoc.create_default_workflow()
    return hoc
