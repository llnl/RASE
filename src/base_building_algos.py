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
import itertools

from PySide6.QtCore import QCoreApplication
from typing import Union, Self
from lxml import etree
from src import rase_functions as Rf
from src import spectrum_file_reading as reading
from src.rase_functions import get_ET_from_file, compress_counts
from src.rebin import rebin
from src.utils import indent
import numpy
import re
import os.path
from glob import glob
from mako.template import Template
from src.table_def import SecondarySpectrum
from src.spectrum_file_reading import readSpectrumFile, BaseSpectraFormatException
from types import SimpleNamespace
import numpy as np
from dataclasses import dataclass

# translation_tag = 'bba'

base_template = '''<?xml version="1.0"?>
<RadInstrumentData>
  <RadMeasurement id="Foreground">
    <MeasurementClassCode>Foreground</MeasurementClassCode>
    <RealTimeDuration>${realtime}</RealTimeDuration>
    <Spectrum>
      <LiveTimeDuration Unit="sec">${livetime}</LiveTimeDuration>
      <ChannelData>${spectrum}</ChannelData>
      ${RASE_sens} ${FLUX_sens}
    </Spectrum>
  </RadMeasurement>
  <EnergyCalibration>
    <CoefficientValues>${ecal}</CoefficientValues>
  </EnergyCalibration>
%for name, secondary in secondaries.items():
  <RadMeasurement id="${name}">
    <MeasurementClassCode>${secondary.classcode}</MeasurementClassCode>
    <RealTimeDuration>PT${secondary.realtime}S</RealTimeDuration>
    <Spectrum>
      <LiveTimeDuration Unit="sec">PT${secondary.livetime}S</LiveTimeDuration>
      <ChannelData>${secondary.get_counts_as_str()}</ChannelData>
    </Spectrum>
  </RadMeasurement>
%endfor
%for line in additional.splitlines():
  ${line}
%endfor${additional}
</RadInstrumentData>
'''

# Expected yaml fields:
# measurement_spectrum_xpath
# realtime_xpath
# livetime_xpath
# calibration
# subtraction_spectrum_xpath (optional)
# secondary_spectrum_xpath (optional)

pcf_config_txt = 'PCF File'
default_config = {
    'default n42':
        {
            'measurement_spectrum_xpath': './RadMeasurement[MeasurementClassCode="Foreground"]/Spectrum',
            'realtime_xpath': './RadMeasurement[MeasurementClassCode="Foreground"]/RealTimeDuration',
            'livetime_xpath': './RadMeasurement[MeasurementClassCode="Foreground"]/Spectrum/LiveTimeDuration',
            'calibration': './EnergyCalibration/CoefficientValues',
            'subtraction_spectrum_xpath': './RadMeasurement[@id="Foreground"]/Spectrum',
            'additionals': ['./RadMeasurement[MeasurementClassCode="Background"]',
                            './RadMeasurement[MeasurementClassCode="IntrinsicActivity"]'
                            ]
        },
    'rase n42':
        {
            'measurement_spectrum_xpath': './RadMeasurement[@id="Foreground"]/Spectrum',
            'realtime_xpath': './RadMeasurement[@id="Foreground"]/RealTimeDuration',
            'livetime_xpath': './RadMeasurement[@id="Foreground"]/Spectrum/LiveTimeDuration',
            'calibration': './EnergyCalibration/CoefficientValues',
            'subtraction_spectrum_xpath': './RadMeasurement[@id="Foreground"]/Spectrum',
            'additionals': ['./RadMeasurement[MeasurementClassCode="Background"]',
                            './RadMeasurement[MeasurementClassCode="IntrinsicActivity"]'
                            ]
        }
}

pcf_config = {
    pcf_config_txt:  # We will translate PCF files into n42s
        {
            'measurement_spectrum_xpath': './RadMeasurement/Spectrum',
            'realtime_xpath': './RadMeasurement/Spectrum/RealTimeDuration',
            'livetime_xpath': './RadMeasurement/Spectrum/LiveTimeDuration',
            'calibration': './EnergyCalibration/CoefficientValues',
            'subtraction_spectrum_xpath': './RadMeasurement/Spectrum',
        }
}


@dataclass
class rawValues:  #TODO: add neutron sensitivity
    counts: np.ndarray
    realtime: float
    livetime: float
    ecal: tuple[4]
    secondaries: dict
    additional: str
    RASE_sens: str
    FLUX_sens: str
    uSievertsph: float
    fluxValue: float

    def __add__(self, other: Self):

        realtime = self.realtime+other.realtime
        livetime = self.livetime+other.livetime
        ecal=self.ecal
        if not np.all(other.ecal == ecal):
            counts = self.counts + rebin_from_cal(other.counts, other.ecal, ecal)
        else:
            counts = self.counts + other.counts
        secondaries = self.secondaries
        additional = self.additional
        weighted_uSievertsph = (self.uSievertsph*self.livetime + other.uSievertsph*other.livetime) / livetime if self.uSievertsph and other.uSievertsph else None
        weighted_Flux = (self.fluxValue*self.livetime + other.fluxValue*other.livetime) / livetime if self.fluxValue and other.fluxValue else None
        RASE_sens, FLUX_sens = sensitivity_text(counts, livetime, weighted_uSievertsph, weighted_Flux)

        output = rawValues(counts= counts,realtime=realtime, livetime=livetime, ecal=ecal, secondaries=secondaries ,
                           additional=additional , RASE_sens=RASE_sens, FLUX_sens=FLUX_sens,
                           uSievertsph=weighted_uSievertsph, fluxValue=weighted_Flux)

        return output

    def background_subtract(self, other):
        if (other.ecal != self.ecal).any():
            counts_other = rebin_from_cal(other.counts, other.ecal, self.ecal)
        else:
            counts_other = other.counts
        counts = subtract_spectra(counts_m=self.counts, livetime_m=self.livetime, counts_b=counts_other, livetime_b=other.livetime)

        output = rawValues(counts=counts, realtime=self.realtime, livetime=self.livetime, ecal=self.ecal, secondaries=self.secondaries,
                           additional=self.additional, RASE_sens=self.RASE_sens, FLUX_sens=self.FLUX_sens,
                           uSievertsph=self.uSievertsph, fluxValue=self.fluxValue)
        return output

def rawvalues_from_basespec(spectrum):
    return rawValues(counts=spectrum.counts, realtime = spectrum.realtime,
                     livetime=spectrum.livetime, ecal=(spectrum.ecal0, spectrum.ecal1, spectrum.ecal2, spectrum.ecal3),
                     secondaries=dict(), additional='', RASE_sens=spectrum.rase_sensitivity,
                     FLUX_sens=spectrum.flux_sensitivity, uSievertsph=1 if spectrum.rase_sensitivity else 0,
                     fluxValue=1 if spectrum.flux_sensitivity else 0)

def rebin_from_cal(counts, old_cal, new_cal):
    old_energies = numpy.polyval(numpy.flip(old_cal), numpy.arange(len(counts) + 1))
    return rebin(counts, old_energies, new_cal)



def uncompressCountedZeroes(counts):
    """
    Standard CountedZeroes uncompress method.
    Similar to implementations elsewhere in RASE code, but this one a) does not confirm
    CounterZeroes compression is in use and b) outputs to a numpy ndarray
    @param counts:
    @return:
    """
    uncompressedCounts = []
    counts_iter = iter(counts)
    for count in counts_iter:
        if count == float(0):
            uncompressedCounts.extend([0] * int(next(counts_iter)))
        else:
            uncompressedCounts.append(count)
    return numpy.fromiter(uncompressedCounts, float)


def get_counts(specEl):
    """
    Retrieve counts as a numpy ndarray from the first ChannelData element in the given Spectrum
    element. Calls Uncompress method if the ChannelData element has an attribute containing
    "compression" equal to "CountedZeroes".
    @param specEl:
    @return:
    """
    chandataEl = reading.requiredElement('ChannelData', specEl)
    # print(etree.tostring(chandataEl, encoding='unicode', method='xml'))

    try:
        dataEl = reading.requiredElement('Data', chandataEl)
    except reading.BaseSpectraFormatException:
        dataEl = chandataEl

    counts = numpy.fromstring(dataEl.text, float, sep=' ')
    for attribute, value in dataEl.attrib.items():
        if 'COMPRESSION' in attribute.upper() and value == 'CountedZeroes':
            return uncompressCountedZeroes(counts)
    else:
        return counts


def get_livetime(specEl):
    """
    Retrieves Livetime as a float from the Spectrum element
    @param specEl:
    @return:
    """
    timetext = reading.requiredElement(('LiveTimeDuration', 'LiveTime'), specEl).text
    return Rf.ConvertDurationToSeconds(timetext)


def subtract_spectra(counts_m, livetime_m, counts_b, livetime_b):
    """
    Given two count arrays and their associated livetimes, returns an ndarray of the counts
    in the first minus the counts i nthe seccond weighted by the relative livetimes.
    Negative values are later set to zero.
    """
    # FIXME: should allow correction for different effects of dead times between the two spectra
    counts_s = counts_m - (counts_b) * (livetime_m / livetime_b)
    return counts_s


def insert_counts(specEl, counts):
    """
    Adds ChannelData element to Spectrum element with the given counts. Removes all previously
    existing ChannelData elements.
    @param specEl:
    @param counts:
    @return:
    """
    for parent in specEl.findall('.//ChannelData/..'):
        for element in parent.findall('ChannelData'):
            parent.remove(element)
    countsEl = etree.Element('ChannelData')
    if all(counts.astype(float) == counts.astype(int)):
        # TODO: Make a switch to decide whether int or float
        countstxt = ' '.join(f'{round(count)}' for count in [0 if c < 0 else c for c in counts])
    else:
        countstxt = ' '.join(f'{count:.4f}' for count in counts)
    countsEl.text = countstxt
    specEl.append(countsEl)


def calc_RASE_Sensitivity(counts, livetime, source_act_fact):
    """
    Derived from the documentation formula for calcuating RASE Sensitivity.
    For dose, source_act_fact is microsieverts/hour
    For flux, source_act_fact is counts*cm^-2*s-1 in the photopeak of interest
    @param counts:
    @param livetime:
    @param uSievertsph:
    @return:
    """
    return (counts.sum() / livetime) / source_act_fact


def sensitivity_text(counts, livetime, uSievertsph=None, fluxValue=None, ):
    """
    Calculate and then plug in in the sensitivity values
    @param counts:
    @param livetime:
    @param uSievertsph:
    @param fluxValue:
    @return:
    """
    # TODO: Make so that if the user puts nothing in dose or flux an error gets thrown
    # TODO: refactor to separate out text formatting and value extraction
    RASE_sensitivity = ''
    FLUX_sensitivity = ''
    if uSievertsph:
        Rsens = calc_RASE_Sensitivity(counts, livetime, uSievertsph)
        RASE_sensitivity = f'<RASE_Sensitivity>{Rsens}</RASE_Sensitivity>'
    if fluxValue:
        Rsens = calc_RASE_Sensitivity(counts, livetime, fluxValue)
        FLUX_sensitivity = f'<FLUX_Sensitivity>{Rsens}</FLUX_Sensitivity>'
    if not (uSievertsph or fluxValue):
        Rsens = 1
        RASE_sensitivity = f'<RASE_Sensitivity>{Rsens}</RASE_Sensitivity>'
        FLUX_sensitivity = f'<FLUX_Sensitivity>{Rsens}</FLUX_Sensitivity>'
    return RASE_sensitivity, FLUX_sensitivity

def get_ET_values(ET, measureXPath, realtimeXPath, livetimeXPath,
                  calibration, additionals=[], secondaries_dict=None,
                  uSievertsph=None, fluxValue=None, transform=None, ndetectors=1):

    specElements = ET.xpath(measureXPath)

    assert len(specElements), f'Found nothing at the measurement_spectrum_xpath: {measureXPath}'

    livetimes = ET.xpath(livetimeXPath)

    #do calibration first, so we can sum spectra later if needed
    try:
        if '@id="FromSpectrum"' in calibration:
            ecals = []
            for spectrum in specElements:
                ecaltag = spectrum.attrib['energyCalibrationReference']
                this_cal_xpath = calibration.replace("FromSpectrum", ecaltag)
                this_cal_els = ET.xpath(this_cal_xpath)
                assert len(this_cal_els)==1, f'Zero or more than one calibration found using @id="FromSpectrum" mode, found { len(this_cal_els)}'
                ecals.append(this_cal_els[0].text)
        else: #most typical case
            ecals = [el.text for el in ET.xpath(calibration)]

        ecalsvals = [[ float(coeff) for coeff in ecal.split()] for ecal in ecals]
        ecals = np.zeros((len(ecalsvals),4))
        for a,l in zip(ecals,ecalsvals):
            a[:len(l)] += l
    except (TypeError, etree.XPathError):
        try:
            calibration = [float(coeff) for coeff in calibration.split()]
        except AttributeError:
            pass
        ecals = np.zeros(1, 4)
        ecals[:len(calibration)]+= calibration

    except (IndexError):
        raise ValueError("Calibration XPath does not resolve to any element in input XML. "
                         "Please check base building config file and compare to the input XML.")

    assert len(ecals) in [1, len(specElements)], f'Found {len(ecals)} calibrations, different than {len(specElements)} spectra. Check config file'

    sumcounts = 0

    for specElement, ecal in zip(specElements, itertools.cycle(ecals)):
        #itertools.cycle(ecals) handles case where there's just one ecal, repeating that one value for all specs
        counts = get_counts(specElement)
        if transform:
            counts = transform(counts)
        if not np.all(ecal == ecals[0]): #all checks all 4 coeffs
            counts = rebin_from_cal(counts, ecal, ecals[0])
        sumcounts = counts + sumcounts # sums everything up, works OK on first iteration

    livetime_sum = sum([Rf.ConvertDurationToSeconds(livetime.text) for livetime in livetimes]) / ndetectors

    # if subtraction_ET:
    #     specElement_b = subtraction_ET.xpath(subtractionXpath)[0]
    #     specElement_b_counts = get_counts(specElement_b)
    #     livetime_bg = get_livetime(specElement_b)
    #     sumcounts = subtract_spectra(sumcounts, livetime_sum_s, specElement_b_counts, livetime_bg)

    realtimes = ET.xpath(realtimeXPath)  # assumes realtime is a property of the radmeasurement
    realtime_sum_s = sum([Rf.ConvertDurationToSeconds(realtime.text) for realtime in realtimes])  # usually there's only one realtime

    RASE_sensitivity, FLUX_sensitivity = sensitivity_text(sumcounts, livetime_sum, uSievertsph, fluxValue)

    additional = ''
    if additionals:
        for addon in additionals:
            secondary_find = ET.xpath(addon)
            if secondary_find:
                secondary_el = ET.xpath(addon)[0]
                etree.indent(secondary_el)
                secondary_el.nsmap.clear()
                additional += etree.tostring(secondary_el, encoding='unicode')
                additional += '\n'

    secondaries = {}
    if secondaries_dict:
        for key, value in secondaries_dict.items():
            sec = SecondarySpectrum(
                realtime=Rf.ConvertDurationToSeconds(ET.xpath(value['realtime'])[0].text),
                livetime=Rf.ConvertDurationToSeconds(ET.xpath(value['livetime'])[0].text),
                classcode=value['classcode']
            )
            spectrum_element = ET.xpath(value['spectrum'])[0]
            sec.counts = get_counts(spectrum_element)
            secondaries[key] = sec

    # remove some fluff that makes it so interspec can't read the spectra:
    pattern = r' radDetectorInformationReference="[^"]+"'
    additional = re.sub(pattern, '', additional)

    output=rawValues(counts=sumcounts, realtime=realtime_sum_s, livetime=livetime_sum,ecal=ecals[0],
                           secondaries=secondaries, additional=additional, RASE_sens=RASE_sensitivity,
                     FLUX_sens=FLUX_sensitivity,uSievertsph=uSievertsph, fluxValue=fluxValue)
    return output

def counts_decimal_format(counts):
    if all(counts.astype(float) == counts.astype(int)):
        # TODO: Make a switch to decide whether int or float
        countstxt = ' '.join(f'{round(count)}' for count in counts)
    else:
        countstxt = ' '.join(f'{count:.4f}' for count in counts)
    return countstxt

def build_base_ET(rawValues: rawValues, device_template=None):
    counts = rawValues.counts.clip(min=0)
    countstxt = counts_decimal_format(counts)

    realtime_sum_txt = Rf.ConvertSecondsToIsoDuration(rawValues.realtime)
    livetime_sum_txt = Rf.ConvertSecondsToIsoDuration(rawValues.livetime)
    template_ecal = ' '.join([str(k) for k in rawValues.ecal])
    secondaries = rawValues.secondaries
    additional = rawValues.additional
    RASE_sensitivity=rawValues.RASE_sens
    FLUX_sensitivity=rawValues.FLUX_sens

    makotemplate = Template(text=base_template, input_encoding='utf-8', strict_undefined=True)
    output = makotemplate.render(spectrum=countstxt, realtime=realtime_sum_txt, livetime=livetime_sum_txt,
                                 ecal=template_ecal, secondaries=secondaries,
                                 additional=additional, RASE_sens=RASE_sensitivity, FLUX_sens=FLUX_sensitivity)

    if device_template:  # used for sending base spectra to another format

        # make these accessible to the device template. Probably some compromise here.
        template_data = {}
        # can't use livetime_sum_txt because it has PT and S in it, which is replicated in templates
        template_data['scenario'] = SimpleNamespace(acq_time=str(rawValues.livetime))
        template_data['detector'] = detector = SimpleNamespace(secondary_spectra=secondaries, ecal0=rawValues.ecal[0],
                                                               ecal1=rawValues.ecal[1], ecal2=rawValues.ecal[2],
                                                               ecal3=rawValues.ecal[3], chan_count=len(counts))
        template_data['sample_counts'] = countstxt
        template_data['compressed_sample_counts'] = ' '.join(f'{round(count)}' for count in compress_counts(rawValues.counts))
        template_data['sample_counts_array'] = counts
        template_data['bin_edges'] = ' '.join(str(v) for v in np.polyval(
            [detector.ecal3, detector.ecal2, detector.ecal1, detector.ecal0], np.arange(detector.chan_count + 1)))
        template_data['secondaries']= rawValues.secondaries
        indexval = 0
        if (rawValues.secondaries and type(rawValues.secondaries) == type(dict()) and
                'background' in [k.lower() for k in rawValues.secondaries.keys()]):
            indexval = [k.lower() for k in rawValues.secondaries.keys()].index('background')
        template_data['secondary_spectrum'] = list(rawValues.secondaries.values())[indexval] if rawValues.secondaries else None #first secondary or none
        output = device_template.render(**template_data)

    return output


def list_spectra(ET):
    """
    Grab all the ids of all the spectra in an element tree
    @param ET:
    @return:
    """
    rads = ET.findall('.//RadMeasurement')
    rad_ids = []
    for rad in rads:
        rad_ids.append(rad.get('id', 'No id provided'))
    return rad_ids


def base_output_filename(manufacturer, model, source, description=None):
    """
    Generic base spectrum output filename
    @param manufacturer:
    @param model:
    @param source:
    @param description:
    @return:
    """
    # if len(manufacturer) >=5:  raise ValueError('Use 4-character manufacturer abbreviation')
    # if len(model) >= 5:        raise ValueError('Use 4-character model abbreviation')
    if description:
        outputname = f'V{manufacturer}_M{model}_{source}_{description}.n42'
    else:
        outputname = f'V{manufacturer}_M{model}_{source}.n42'
    return outputname


def write_base_ET(ET, outputfolder, outputfilename):
    """
    Build structured xml format for base spectrum
    @param ET:
    @param outputfolder:
    @param outputfilename:
    @return:
    """
    outputpath = os.path.join(outputfolder, outputfilename)
    ET.write(outputpath, encoding='utf-8', method='xml', xml_declaration=True)


def write_base_text(text, outputfolder, outputfilename):
    """
    Export the base spectrum .xml structure
    @param text:
    @param outputfolder:
    @param outputfilename:
    @return:
    """
    outputpath = os.path.join(outputfolder, outputfilename)
    with open(outputpath, 'w', newline='') as f:
        f.write(text)


def do_all(inputfile, config: dict, outputfolder, manufacturer, model, source, subtraction, subtraction_config=None,
           uSievertsph=None, fluxValue=None, description=None, transform=None):
    """
    Grab the spectrum info from the raw file, format it to base spectrum form, then write it.
    @param inputfile:
    @param config:
    @param outputfolder:
    @param manufacturer:
    @param model:
    @param source:
    @param subtraction:
    @param uSievertsph:
    @param fluxValue:
    @param description:
    @param transform:
    @return:
    """
    ET = get_ET_from_file(inputfile)
    values = get_ET_values(ET=ET, measureXPath=config['measurement_spectrum_xpath'],
                           realtimeXPath=config['realtime_xpath'], livetimeXPath=config['livetime_xpath'],
                           calibration=config['calibration'],
                           additionals=config.get('additionals'), secondaries_dict=config.get('secondaries'),
                           uSievertsph=uSievertsph, fluxValue=fluxValue, transform=transform)
    try:
        subtraction_ET = get_ET_from_file(subtraction)
    except TypeError:
        subtraction_ET = subtraction
    if subtraction_ET:
        if subtraction_config is None: subtraction_config = config
        subtract_values = get_ET_values(ET=subtraction_ET,
                                        measureXPath=subtraction_config['subtraction_spectrum_xpath'],
                                        realtimeXPath=subtraction_config['realtime_xpath'],
                                        livetimeXPath=subtraction_config['livetime_xpath'],
                                        calibration=subtraction_config['calibration'],
                                        additionals=None, secondaries_dict=None,
                                        uSievertsph=None, fluxValue=None, transform=transform)
        values = values.background_subtract(subtract_values)

    output = build_base_ET(rawValues=values)
    outputfilename = base_output_filename(manufacturer, model, source, description)
    write_base_text(output, outputfolder, outputfilename)



def do_list(inputfiles, config:dict, outputfolder, manufacturer, model, source, subtraction, subtraction_config=None,
           uSievertsph=None, fluxValue=None, description=None, transform=None, master_ecal=None):

    values = [get_ET_values(ET=get_ET_from_file(inputfile), measureXPath=config['measurement_spectrum_xpath'],
                           realtimeXPath=config['realtime_xpath'], livetimeXPath=config['livetime_xpath'],
                            calibration=config['calibration'],
                           additionals=config.get('additionals'), secondaries_dict=config.get('secondaries'),
                           uSievertsph=uSievertsph, fluxValue=fluxValue, transform=transform)
              for inputfile in inputfiles]

    try:
        subtraction_ET = get_ET_from_file(subtraction)
    except TypeError:
        subtraction_ET = subtraction

    sum_values = sum(values[1:], start=values[0]) #funny construciton because you can't use default start=0.

    if subtraction_ET:
        if subtraction_config is None: subtraction_config = config
        subtract_values = get_ET_values(ET=subtraction_ET, measureXPath=subtraction_config['subtraction_spectrum_xpath'],
                                        realtimeXPath=subtraction_config['realtime_xpath'], livetimeXPath=subtraction_config['livetime_xpath'],
                                        calibration=subtraction_config['calibration'],
                                        additionals=None, secondaries_dict=None,
                                        uSievertsph=None, fluxValue=None, transform=transform)
        sum_values = sum_values.background_subtract(subtract_values)

    outputfilename = base_output_filename(manufacturer, model, source, description)
    outET = build_base_ET(rawValues=sum_values)
    write_base_ET(etree.ElementTree(etree.fromstring(bytes(outET, encoding='utf-8'))), outputfolder, outputfilename)
    return master_ecal


def do_glob(inputfileglob, config: dict, outputfolder, manufacturer, model, source, subtraction, subtraction_config=None,
           uSievertsph=None, fluxValue=None, description=None, transform=None, master_ecal=None):
    inputfiles = glob(inputfileglob)
    master_ecal = do_list(inputfiles, config, outputfolder, manufacturer, model, source, subtraction,subtraction_config,
           uSievertsph, fluxValue, description, transform, master_ecal)
    return master_ecal


from .base_spectra_dialog import SharedObject
def validate_output(outputfolder, manufacturer, model, source, description=None):
    outputfilename = os.path.join(outputfolder, base_output_filename(manufacturer, model, source, description))
    sharedobj = SharedObject(True)
    tstatus=[]
    v = readSpectrumFile(filepath=outputfilename, sharedObject=sharedobj, tstatus=tstatus)
    if len(tstatus):
        raise BaseSpectraFormatException(tstatus)
    if not v:
        raise BaseSpectraFormatException("readSpectrumFile returned no output")