import numpy as np
from src.table_def import Session,  Spectrum
def neutron_foreground(scenario, detector):

    scenmats = scenario.scen_materials + scenario.scen_bckg_materials
    detspecs = detector.base_spectra
    time = scenario.acq_time

    return neutron_poisson(scenmats,detspecs,time)


def neutron_background(scenario, detector, livetime):

    scenmats = scenario.scen_bckg_materials
    detspecs = detector.base_spectra
    time = livetime

    return neutron_poisson(scenmats,detspecs,time)

def neutron_poisson(scenmats, detspecs,time ):
    neutron_expectation = 0
    for scenMaterial in scenmats:
        if scenMaterial.neutron_dose:
            baseSpectrum = [b for b in detspecs if b.material_name == scenMaterial.material_name]
            if baseSpectrum:
                baseSpectrum = baseSpectrum[0]
                if baseSpectrum.neutron_sensitivity:
                    this_expectation = scenMaterial.neutron_dose * time * baseSpectrum.neutron_sensitivity
                    neutron_expectation += this_expectation

    neutron_sample = np.random.poisson(neutron_expectation)

    return neutron_sample, neutron_expectation

def any_neutrons_in_db():
    session=Session()
    spectra = session.query(Spectrum).filter(Spectrum.neutrons>0).all()
    return spectra


