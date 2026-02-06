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
This module defines persistable objects in sqlalchemy framework
"""
import enum
import random
import string

from sqlalchemy import ForeignKey, Column, Integer, String, Float, Boolean, Enum, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, sessionmaker, scoped_session, backref, Mapped
from sqlalchemy.sql.schema import Table, CheckConstraint
from sqlalchemy import event, and_
import numpy as np
import hashlib
from typing import Set, Sequence, MutableSequence
import json

from src.datadir_view import DataDirViewManager
from src.utils import compress_counts
from typing import List, Optional

DB_VERSION_NAME = 'rase_db_v3_1_2'

class Base(DeclarativeBase):
    # see https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#migrating-an-existing-mapping
    __allow_unmapped__ = True
    pass

# Session = sessionmaker()

# This allows access to sessions when multithreading
session_factory = sessionmaker()
Session = scoped_session(session_factory)

# These form many-to-many association tables
scen_infl_assoc_tbl = Table('scenario_influences', Base.metadata,
    Column('scenario_id',    Integer, ForeignKey('scenarios.id')),
    Column('influence_name', String, ForeignKey('influences.name')))

det_infl_assoc_tbl = Table('det_influences', Base.metadata,
    Column('det_id', String, ForeignKey('detectors.id')),
    Column('influence_name', String, ForeignKey('influences.name')))

scen_group_assoc_tbl = Table('scen_group_association', Base.metadata,
    Column('group_id', Integer, ForeignKey('scenario_groups.id',ondelete='cascade')),
    Column('scenario_id', String, ForeignKey('scenarios.id', ondelete='cascade'))
)

replay_detector_assoc_tbl = Table('replay_detector_assoc', Base.metadata,
    Column('replay_id', String(8), ForeignKey('replays.id'), primary_key=True),
    Column('detector_id', String(8), ForeignKey('detectors.id'), primary_key=True)
)

def generate_random_string(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


class CorrespondenceTableElement(Base):
    __tablename__   = 'correspondence_table_element'
    id              = mapped_column(Integer, primary_key=True)
    isotope         = mapped_column(String)
    corrList1       = mapped_column(String)
    corrList2       = mapped_column(String)
    corr_table_name = mapped_column(String, ForeignKey('correspondence_table.name'))
    corr_table = relationship('CorrespondenceTable',backref='corr_table_elements')

    def __init__(self, isotope, table, corrList1=None, corrList2=None):
        self.isotope = isotope
        self.corr_table = table
        self.corrList1 = ''
        self.corrList2 = ''
        if corrList1: self.corrList1 = corrList1
        if corrList2: self.corrList2 = corrList2


class CorrespondenceTable(Base):
    __tablename__   = 'correspondence_table'
    name            = mapped_column(String, primary_key=True)
    is_default = mapped_column(Boolean, default=False, nullable=False)

@event.listens_for(CorrespondenceTable, "after_insert")
@event.listens_for(CorrespondenceTable, "after_update")
def _check_default(mapper, connection, target):
    if target.is_default:
        connection.execute(
            CorrespondenceTable.__table__.
                update().
                values(is_default=False).
                where(CorrespondenceTable.name != target.name)
        )


class Material(Base):
    __tablename__ = 'materials'
    name          = mapped_column(String, primary_key=True)
    include_intrinsic = mapped_column(Boolean, nullable=False)

    def __init__(self, name, include_intrinsic=False):
        self.name = self.get_name(name, include_intrinsic)
        self.include_intrinsic = include_intrinsic

    # the workaround to avoid significant refactoring of the database and code
    @staticmethod
    def get_name(name, include_intrinsic=False):
        return name + '-wIntrinsic' if include_intrinsic else name

    def name_no_shielding(self) -> Set[str]:
        return set(self.name.split("-")[0].split("+"))


class Influence(Base):
    __tablename__ = 'influences'
    name          = mapped_column(String, primary_key=True)


class Scenario(Base):
    __tablename__       = 'scenarios'
    id                  = mapped_column(String, primary_key=True)
    acq_time            = mapped_column(Float)
    replication         = mapped_column(Integer)
    shielding_material  = mapped_column(String)
    shielding_thickness = mapped_column(Float, nullable=False, default=0)
    comment             = mapped_column(String)
    # eager loading required by the import/export scenario functions in scenarios_io module
    scen_materials      = relationship('ScenarioMaterial', cascade='all, delete', lazy='joined')
    scen_bckg_materials = relationship('ScenarioBackgroundMaterial', cascade='all, delete', lazy='joined')
    influences          = relationship('Influence', secondary=scen_infl_assoc_tbl, lazy='joined')
    scenario_groups     = relationship('ScenarioGroup', secondary=scen_group_assoc_tbl, backref='scenarios')
    scenario_class = mapped_column(Integer)
    __mapper_args__ = {
        'polymorphic_identity': 'scenario',
        'polymorphic_on': scenario_class
    }

    def __init__(self, acq_time=1, replication=1, scen_materials=[], scen_bckg_materials=[], influences=[],
                 scenario_groups=[], shielding_material='', shielding_thickness=0, comment=''):
        # id: a hash of scenario parameters, truncated to a 6-digit hex string
        self.id = self.scenario_hash(acq_time, scen_materials, scen_bckg_materials, influences,
                                     shielding_material, shielding_thickness)
        self.acq_time = acq_time
        self.replication = replication  # number of sample spectra to create
        self.influences = influences
        self.scen_materials = scen_materials
        self.scen_bckg_materials = scen_bckg_materials
        self.scenario_groups = scenario_groups
        self.shielding_material = shielding_material
        self.shielding_thickness = shielding_thickness
        self.comment = comment

    @staticmethod
    def scenario_hash(acq_time, scen_materials, scen_bckg_materials, influences=[], shield_mat='', shield_thick=0):
        s = f'{acq_time}' + \
            ''.join(sorted('SRC{}{:9.12f}{}'.format(
                scenMat.material.name, scenMat.dose, scenMat.fd_mode, scenMat.neutron_dose) for scenMat in scen_materials)) + \
            ''.join(sorted('BKGD{}{:9.12f}{}'.format(
                scenMat.material.name, scenMat.dose, scenMat.fd_mode, scenMat.neutron_dose) for scenMat in scen_bckg_materials)) + \
            ''.join(sorted(infl.name for infl in influences)) + ('' if not shield_thick else shield_mat) + f'{shield_thick}'
        try:
            return hashlib.md5(s.encode('utf-8')).hexdigest()[:6].upper()
        except ValueError:
            return hashlib.md5(s.encode('utf-8'),usedforsecurity=False).hexdigest()[:6].upper()

    def get_label(self) -> str:
        """
        Return a simple readable label with scenario definition
        Note: label does not include neutron_dose or influences
        """
        s = ('_'.join(sorted(f'{sm.material.name}({sm.dose:.2e}{sm.fd_mode[0]})' for sm in self.scen_materials)) +
             '__' +
             '_'.join(sorted(f'{sm.material.name}({sm.dose:.2e}{sm.fd_mode[0]})' for sm in self.scen_bckg_materials)) +
             f'_{int(self.acq_time):d}s' +
             f'_{int(self.replication):d}'
        )
        return s

    def get_material_names_no_shielding(self) -> Set[str]:
        return set(name for scenMat in self.scen_materials for name in scenMat.material.name_no_shielding())

    def get_bckg_material_names_no_shielding(self) -> Set[str]:
        return set(name for scenMat in self.scen_bckg_materials for name in scenMat.material.name_no_shielding())


class SampleSpectraSeed(Base):
    __tablename__='sample_spectra_seeds'
    id       = mapped_column(Integer, primary_key=True)
    seed     = mapped_column(Integer)
    scenario = relationship('Scenario')
    detector = relationship('Detector', backref='sample_spectra_seed', cascade='all')
    scen_id  = mapped_column(String, ForeignKey('scenarios.id', ondelete='cascade'))
    det_name = mapped_column(String, ForeignKey('detectors.name', ondelete='cascade', onupdate='cascade'))


class ScenarioGroup(Base):
    __tablename__= 'scenario_groups'
    id          = mapped_column(Integer, primary_key=True)
    name        = mapped_column(String, unique=True)
    description = mapped_column(String)


class ScenarioMaterial(Base):
    """many-to-many table between scenario and material"""
    __tablename__ = 'scenario_materials'
    id            = mapped_column(Integer, primary_key=True)
    dose          = mapped_column(Float)
    neutron_dose  = mapped_column(Float, nullable=False, default=0)
    fd_mode       = mapped_column(String, CheckConstraint("fd_mode IN ('DOSE','FLUX')"))
    material      = relationship('Material', lazy='joined')
    scenario_id   = mapped_column(String, ForeignKey('scenarios.id', ondelete='cascade'))
    material_name = mapped_column(String, ForeignKey('materials.name',ondelete='cascade'))

class ScenarioBackgroundMaterial(Base):
    """many-to-many table between scenario and material"""
    __tablename__ = 'scenario_background_materials'
    id            = mapped_column(Integer, primary_key=True)
    dose          = mapped_column(Float)
    neutron_dose  = mapped_column(Float, nullable=False, default=0)
    fd_mode       = mapped_column(String, CheckConstraint("fd_mode IN ('DOSE','FLUX')"))
    material      = relationship('Material', lazy='joined')
    scenario_id   = mapped_column(String, ForeignKey('scenarios.id',ondelete='cascade'))
    material_name = mapped_column(String, ForeignKey('materials.name',ondelete='cascade'))

class Detector(Base):
    __tablename__= 'detectors'

    id           = mapped_column(String(8), primary_key=True, default=generate_random_string)
    name         = mapped_column(String, unique=True, nullable=False)
    manufacturer = mapped_column(String)
    class_code   = mapped_column(String)
    hardware_version = mapped_column(String)
    instr_id     = mapped_column(String)
    chan_count   = mapped_column(Integer)
    ecal0        = mapped_column(Float) #These are now "preferred" ecals. When multiple sources have different ecals, we rebin to the detector's preferred ecal.
    ecal1        = mapped_column(Float)
    ecal2        = mapped_column(Float)
    ecal3        = mapped_column(Float)
    includeSecondarySpectrum = mapped_column(Boolean)
    secondary_type = mapped_column(Integer)    # 0=long_back from basespec, 1=long_back from scen, 2=long_back from file
    secondary_classcode = mapped_column(String)
    sample_intrinsic = mapped_column(Boolean)
    intrinsic_classcode = mapped_column(String)
    shielding_drf   = mapped_column(String)
    influences          = relationship('Influence', secondary=det_infl_assoc_tbl, cascade='all', lazy='joined', backref='detectors')
    base_spectra : Mapped[List['BaseSpectrum']] = relationship('BaseSpectrum',primaryjoin=lambda: and_(BaseSpectrum.detector_name == Detector.name,BaseSpectrum.spectrum_type == 'base_spectrum'),backref='detectors', lazy='joined', foreign_keys='BaseSpectrum.detector_name')
    base_spectra_xyz : Mapped[List['BaseSpectrumXYZ']] = relationship('BaseSpectrumXYZ',backref='detectors', foreign_keys='BaseSpectrumXYZ.detector_name')
    bckg_spectrum_id = mapped_column(Integer, ForeignKey('spectra.id'), nullable=True) #need a key here, since we can't say that whatever Spectrum has detector_name = this detector is the bckg spectrum for this one.
    bckg_spectrum : Mapped[Optional['Spectrum']] = relationship('Spectrum', foreign_keys=bckg_spectrum_id, post_update=True) #spectrum that will be filled into the "included secondary" slot during spectral generation / templating
    bckg_spectra_dwell = mapped_column(Integer, default=0)
    bckg_spectra_resample = mapped_column(Boolean, default=True)  # resampling the background at each replication?
    secondary_spectra : Mapped[List['SecondarySpectrum']] = relationship('SecondarySpectrum',backref='detectors', foreign_keys='SecondarySpectrum.detector_name')
    replays: Mapped[List['Replay']] = relationship('Replay', secondary=replay_detector_assoc_tbl, back_populates='detectors', lazy='joined')

    __table_args__ =  (UniqueConstraint('name'),)

    @property
    def ecal(self):
        return np.array([self.ecal0, self.ecal1, self.ecal2, self.ecal3])

    @ecal.setter
    def ecal(self, value):
        self.ecal0, self.ecal1, self.ecal2, self.ecal3 = value

    def scenariomaterial_is_allowed(self, scen_mat: ScenarioMaterial):
        """
        Compare the material and dose of the given ScenarioMaterial object against the list of base spectra.
        Returns: True if the base spectrum for the material exists, has the proper sensitivity factor, and has the
        correct dose or flux value if the material includes an intrinsic source. False otherwise.
        """
        base_spectrum = [b for b in self.base_spectra if b.material_name == scen_mat.material.name]
        if not base_spectrum:
            return False
        if (isinstance(base_spectrum[0].rase_sensitivity, float) and scen_mat.fd_mode == 'DOSE') or \
                (isinstance(base_spectrum[0].flux_sensitivity, float) and scen_mat.fd_mode == 'FLUX'):
            if scen_mat.material.include_intrinsic:
                v = 0 if scen_mat.fd_mode == 'DOSE' else 1
                if scen_mat.dose != base_spectrum[0].get_measured_dose_and_flux()[v]:
                    return False
            return True
        return False

    def add_replay(self, replay: 'Replay'):
        if replay not in self.replays:
            self.replays.append(replay)

    def remove_replay(self, replay: 'Replay'):
        if replay not in self.replays:
            self.replays.remove(replay)


class DetectorInfluence(Base):
    __tablename__   = 'detector_influences'
    id              = mapped_column(Integer, primary_key=True)
    infl_0          = mapped_column(Float)
    infl_1          = mapped_column(Float)
    infl_2          = mapped_column(Float)
    fixed_smear     = mapped_column(Float)
    linear_smear    = mapped_column(Float)
    degrade_infl0   = mapped_column(Float)
    degrade_infl1   = mapped_column(Float)
    degrade_infl2   = mapped_column(Float)
    degrade_f_smear = mapped_column(Float)
    degrade_l_smear = mapped_column(Float)
    influence       = relationship('Influence', backref=backref("detector_influence",uselist=False), cascade="all,delete", uselist=False)
    influence_name  = mapped_column(String, ForeignKey('influences.name'))


class ReplayTypes(enum.Enum):
    standalone = 0
    gadras_web = 1

class ConfidenceTypes(enum.Enum):
    discrete = 0
    continuous = 1

class Replay(Base):
    __tablename__  = 'replays'
    id           = mapped_column(String(8), primary_key=True, default=generate_random_string)
    name           = mapped_column(String, unique=True, nullable=False)
    type           = mapped_column(Enum(ReplayTypes), default=ReplayTypes.standalone)
    exe_path       = mapped_column(String)
    is_cmd_line    = mapped_column(Boolean)
    settings       = mapped_column(String)
    n42_template_path   = mapped_column(String)
    input_filename_suffix = mapped_column(String)
    web_address = mapped_column(String)
    drf_name = mapped_column(String)
    translator_exe_path = mapped_column(String)
    translator_is_cmd_line = mapped_column(Boolean)
    translator_settings = mapped_column(String)
    detectors: Mapped[List['Detector']] = relationship('Detector', secondary=replay_detector_assoc_tbl, back_populates='replays', lazy='joined')

    use_confidence = mapped_column(Boolean, default=False)
    confidence_mode = mapped_column(Enum(ConfidenceTypes), default=ConfidenceTypes.discrete)

    confidence_scale_default_map = {'low': 1 / 3, 'medium': 2 / 3, 'high': 1}
    confidence_scale_default_range = [[0,10],[0,1]]
    confidence_scale_map = Column(JSON, default=confidence_scale_default_map)
    confidence_scale_range = Column(JSON, default=confidence_scale_default_range)

    def settings_str_u(self):
        """Settings string independent of the replay type"""
        if self.type == ReplayTypes.standalone:
            return self.settings
        elif self.type == ReplayTypes.gadras_web:
            return self.web_address + " | " + self.drf_name

    def is_defined(self):
        """Is Replay Tool Defined?"""
        if self.type == ReplayTypes.standalone and self.exe_path:
            return True
        elif self.type == ReplayTypes.gadras_web and self.web_address:
            return True

    def is_runnable(self):
        """Is Replay Tool Runnable from within RASE?"""
        if self.type == ReplayTypes.standalone:
            return self.is_cmd_line
        elif self.type == ReplayTypes.gadras_web:
            return True

    def add_to_detector(self, detector: 'Detector'):
        if detector not in self.detectors:
            self.detectors.append(detector)

    def remove_from_detector(self, detector: 'Detector'):
        if detector in self.detectors:
            self.detectors.remove(detector)

class Spectrum(Base):
    __tablename__ = 'spectra'
    id            = mapped_column(Integer, primary_key=True)
    filename      = mapped_column(String)
    baseCounts    = mapped_column(String)
    realtime      = mapped_column(Float)
    livetime      = mapped_column(Float)
    ecal0         = mapped_column(Float)
    ecal1         = mapped_column(Float)
    ecal2         = mapped_column(Float)
    ecal3         = mapped_column(Float)
    spectrum_type = mapped_column(Integer)
    neutrons = mapped_column(Float, nullable=True, default=0)

    detector_name = mapped_column(String, ForeignKey('detectors.name', ondelete='cascade', onupdate='cascade'))

    __mapper_args__ = {
        'polymorphic_identity': 'spectrum',
        'polymorphic_on': spectrum_type
    }

    def __init__(self, other: 'Spectrum' = None, **kwargs):
        """
        Optionally initialize this instance by copying attributes from another Spectrum instance.
        Keyword arguments override any copied values.
        """
        if other is not None:
            # Copy all column attributes except 'id' by default
            for key in inspect(self.__class__).columns.keys():
                if key != 'id' and hasattr(other, key):
                    setattr(self, key, getattr(other, key))
        # Override with any explicitly provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    @declared_attr
    def material(cls): return relationship('Material')
    #
    # @declared_attr
    # def detector_name(cls):
    #     return mapped_column(String, ForeignKey('detectors.name', ondelete='cascade', onupdate='cascade'))

    def is_spectrum_float(self):
        """Checks if spectrum has floats in it or not"""
        for binval in self.baseCounts.split(','):
            c = float(binval)
            if c and (c < 1 or int(c) % c):
                return True
        return False

    @declared_attr
    def material_name(cls): return mapped_column(String, ForeignKey('materials.name', ondelete='cascade'), nullable=True)

    def as_json(self):
        return json.dumps([{"title": self.material_name,
                            "livetime": self.livetime,
                            "realtime": self.realtime,
                            "xeqn": list(self.ecal),
                            "y": [float(c) for c in self.baseCounts.split(',')],
                            "yScaleFactor": 1,
                            }])

    @property
    def counts(self):
        return np.array([float(c) for c in self.baseCounts.split(",")])
    @counts.setter
    def counts(self, value):
        self.baseCounts = ','.join([str(c) for c in value])

    @property
    def ecal(self):
        return np.array([self.ecal0, self.ecal1, self.ecal2, self.ecal3])
    @ecal.setter
    def ecal(self,value):
        value = list(value)
        value += [0]* (4-len(value))
        self.ecal0, self.ecal1, self.ecal2, self.ecal3 = value

    #legacy
    def get_counts_as_np(self)->Sequence[float]:
        return np.array([float(c) for c in self.baseCounts.split(",")])

    #legacy
    def get_counts_as_str(self):
        if self.is_spectrum_float():
            return ' '.join([str(float(c)) for c in self.baseCounts.split(",")])
        else:
            return ' '.join([str(int(float(c))) for c in self.baseCounts.split(",")])


    def get_compressed_counts_as_str(self):
        if self.is_spectrum_float():
            return ' '.join('{:f}'.format(x) for x in
                            compress_counts(np.array([float(c) for c in self.baseCounts.split(",")])))
        else:
            return ' '.join('{:d}'.format(x) for x in
                            compress_counts(np.array([int(float(c)) for c in self.baseCounts.split(",")])))

class BaseSpectrum(Spectrum):
    __tablename__ = 'base_spectra'
    __mapper_args__ = {
        'polymorphic_identity': 'base_spectrum',
    }
    id = Column(Integer, ForeignKey('spectra.id', ondelete='CASCADE'), primary_key=True)
    rase_sensitivity = mapped_column(Float)
    flux_sensitivity = mapped_column(Float)
    neutron_sensitivity = mapped_column(Float, nullable=True, default=0)

    def get_measured_dose_and_flux(self):
        """Return dose and flux of the material for the base spectrum creation conditions"""
        intensity_dose = None
        intensity_flux = None
        if self.rase_sensitivity:
            intensity_dose = float(f'{(sum(self.counts) / self.livetime / self.rase_sensitivity):.3g}')
        if self.flux_sensitivity:
            intensity_flux = float(f'{(sum(self.counts) / self.livetime / self.flux_sensitivity):.3g}')
        return intensity_dose, intensity_flux

class BaseSpectrumXYZ(Spectrum):
    __tablename__ = 'base_spectra_xyz'
    __mapper_args__ = {
        'polymorphic_identity': 'base_spectrum_xyz',
    }
    id = Column(Integer, ForeignKey('spectra.id', ondelete='CASCADE'), primary_key=True)
    sensitivity   = mapped_column(Float)
    x             = mapped_column(Float)  # units of cm
    y             = mapped_column(Float)  # units of cm
    z             = mapped_column(Float)  # units of cm


class ShieldedSpectrum(BaseSpectrum):
    __tablename__ = 'shielded_spectra'
    __mapper_args__ = {
        'polymorphic_identity': 'shielded_spectrum',
    }
    id = Column(Integer, ForeignKey('base_spectra.id', ondelete='CASCADE'), primary_key=True)
    shielding_material = mapped_column(String)
    shielding_thickness = mapped_column(Float, nullable=False, default=0)

class SecondarySpectrum(Spectrum):
    __tablename__ = 'secondary_spectra'
    __mapper_args__ = {
        'polymorphic_identity': 'secondary_spectrum',
    }
    id = mapped_column(Integer, ForeignKey('spectra.id', ondelete='CASCADE'), primary_key=True)
    classcode = mapped_column(String)  # aka static efficiency
    # def __init__(self, material, filename, realtime, livetime,baseCounts,ecal):
    #     self.material=material ##TODO: do we need an init here, or will it be taken care of automatically?


class MaterialWeight(Base):
    __tablename__   = 'material_weight'
    name            = mapped_column(String, primary_key=True)
    mat_name        = mapped_column(String)
    TPWF            = mapped_column(Float)
    FPWF            = mapped_column(Float)
    FNWF            = mapped_column(Float)


from sqlalchemy import PickleType

def are_elements_equal(x, y):
    return x == y

class DynamicModelStorage(Base):
    __tablename__ = 'dynamic_models'
    id = mapped_column(Integer, primary_key=True)
    detector_name = mapped_column(String)
    material_name = mapped_column(String)
    model_name    = mapped_column(String)
    model_def     = mapped_column(JSON)
    model = mapped_column(PickleType(comparator=are_elements_equal))
    __table_args__ = (UniqueConstraint('detector_name', 'material_name', 'model_name', 'model_def',
                                       name='_customer_location_uc'),
                      )

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, fields
from marshmallow import fields as mfields

class MaterialSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Material
        load_instance = True

class SpectrumSchema(SQLAlchemyAutoSchema):
    class Meta:
        model=Spectrum
        load_instance=True
        include_relationships = True
        exclude = ("id","spectrum_type")

    material = fields.Nested(MaterialSchema)

class BaseSpectrumSchema(SQLAlchemyAutoSchema):
    class Meta:
        model=BaseSpectrum
        load_instance=True
        include_relationships = True
        exclude = ("id","spectrum_type")

    material = fields.Nested(MaterialSchema)

class SecondarySpectrumSchema(SQLAlchemyAutoSchema):
    class Meta:
        model=SecondarySpectrum
        load_instance=True
        include_relationships = True
        exclude = ("id","spectrum_type","material","filename")

class ReplaySchema(SQLAlchemyAutoSchema):
    class Meta:
        model=Replay
        load_instance=True
        exclude = ("id",) #exclude so we can import without having ID collision
    type = mfields.Enum(ReplayTypes)
    confidence_mode = mfields.Enum(ConfidenceTypes)
    detectors = fields.Nested('DetectorSchema', allow_none=True, many=True, exclude=('replays',))

class DetectorInfluenceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = DetectorInfluence
        load_instance = True
        exclude = ("id",)

class InfluenceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model=Influence
        load_instance=True
    detector_influence = fields.Nested(DetectorInfluenceSchema)

class DetectorSchema(SQLAlchemyAutoSchema):
    class Meta:
        model=Detector
        load_instance=True
        include_relationships = True
        exclude = ("id",) #exclude so we can import without having ID collision
    base_spectra = fields.Nested(BaseSpectrumSchema, many=True, exclude=('detectors',))
    replays = fields.Nested(ReplaySchema, allow_none=True, many=True, exclude=('detectors',))
    influences = fields.Nested(InfluenceSchema, many=True,)
    secondary_spectra = fields.Nested(SecondarySpectrumSchema, many=True, exclude=('detectors',))
    bckg_spectrum = fields.Nested(SpectrumSchema, allow_none=True, many=False, exclude=('material',))

# class ProxySource(Base): #removed for the moment, since I am trying to specify proxies in the train set instead
#     __tablename__ = 'proxy_sources'
#
#     material_name = mapped_column(String,primary_key=True)
#     proxy         = mapped_column(JSON) #dict

# from dynamic.dynamic_table_def import DynamicPathConfig, DynamicScenario


class DBEventHandlerDataView:
    def __init__(self, datadir_view_manager: DataDirViewManager):
        self.datadir_view_manager = datadir_view_manager

        # Register event listeners
        event.listen(Detector, 'after_delete', self.on_detector_delete)
        event.listen(Scenario, 'after_delete', self.on_scenario_delete)
        event.listen(Replay, 'after_delete', self.on_replay_delete)
        event.listen(Detector, 'after_insert', self.on_detector_insert)
        event.listen(Scenario, 'after_insert', self.on_scenario_insert)
        event.listen(Replay, 'after_insert', self.on_replay_insert)
        event.listen(Detector.name, 'set', self.on_detector_name_change)
        event.listen(Replay.name, 'set', self.on_replay_name_change)

    def on_scenario_delete(self, mapper, connection, target):
        # print(f"Scenario {target.id} - {target.get_label()} was deleted")
        self.datadir_view_manager.delete_scenario(target.id)

    def on_replay_delete(self, mapper, connection, target):
        # print(f"Replay {target.id} - {target.name} was delete")
        self.datadir_view_manager.delete_replay(target.id)

    def on_detector_delete(self, mapper, connection, target):
        # print(f"Detector {target.id} - {target.name} was delete")
        self.datadir_view_manager.delete_detector(target.id)

    def on_detector_name_change(self, target, value, old_value, initiator):
        # print(f"Detector name changed from {old_value} to {value}")
        self.datadir_view_manager.update_detector(target.id, value)

    def on_replay_name_change(self, target, value, old_value, initiator):
        # print(f"Replay name changed from {old_value} to {value}")
        self.datadir_view_manager.update_replay(target.id, value)

    def on_detector_insert(self, mapper, connection, target):
        # print(f"Detector {target.id} added with name {target.name}")
        self.datadir_view_manager.add_map_item('detector', target.id, target.name)

    def on_replay_insert(self, mapper, connection, target):
        # print(f"Replay {target.id} added with name {target.name}")
        self.datadir_view_manager.add_map_item('replay', target.id, target.name)

    def on_scenario_insert(self, mapper, connection, target):
        # Reminder: any change to a scenario in the RASE GUI results in a new record being inserted in the db
        #
        # print(f"Scenario {target.id} added with name {target.get_label()}")
        self.datadir_view_manager.update_scenario(target.id, target.get_label())
        # self.datadir_view_manager.add_map_item('scenario', target.id, target.get_label())