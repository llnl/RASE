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

from PySide6.QtCore import QCoreApplication
from typing import Union
from lxml import etree
from src import rase_functions as Rf
from src import spectrum_file_reading as reading
from src.rase_functions import get_ET_from_file, rebin
from src.utils import indent
import numpy
import re
import os.path
from glob import glob
from mako.template import Template
from src.table_def import SecondarySpectrum
from src.spectrum_file_reading import readSpectrumFile, BaseSpectraFormatException

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


def build_base_ET(ET, measureXPath, realtimeXPath, livetimeXPath,
                  subtraction_ET, subtractionXpath, additionals=[], secondaries_dict=None,
                  uSievertsph=None, fluxValue=None, transform=None, ndetectors=1, additional_meas=None,
                  additional_liv=None, ecal_baselines=None, master_ecal=None):

    measpaths = [measureXPath] + additional_meas if type(additional_meas) == list else [measureXPath]
    livpaths = [livetimeXPath] + additional_liv if type(additional_liv) == list else [livetimeXPath]
    subpaths = [subtractionXpath]

    sumcounts_arr = []
    sumlivetimes_arr = []

    for mpath, lpath in zip(measpaths, livpaths):
        specElements = ET.xpath(mpath)
        livetimes = ET.xpath(lpath)
        countslist = []
        for specElement, livetimeElement in zip(specElements, livetimes):
            counts = get_counts(specElement)
            if transform:
                counts = transform(counts)
            countslist.append(counts)

        sumcounts_arr.append(numpy.array([0 if c < 0 else c for c in sum(countslist)]))
        sumlivetimes_arr.append(sum([Rf.ConvertDurationToSeconds(livetime.text) for livetime in livetimes]) / ndetectors)

    livetime_sum_s = sum(sumlivetimes_arr)
    sumcounts = numpy.zeros(len(sumcounts_arr[0]))
    template_ecal = ' '.join([str(k) for k in master_ecal[0]])

    for counts, ecals in zip(sumcounts_arr, ecal_baselines):
        old_ecal = ecals
        old_ecal = old_ecal + [0.] * (4 - len(old_ecal))
        old_energies = numpy.polyval(numpy.flip(old_ecal), numpy.arange(len(sumcounts) + 1))
        sumcounts += rebin(counts, old_energies,  master_ecal[0])

    if subtraction_ET:
        specElement_b = subtraction_ET.xpath(subpaths[0])[0]
        specElement_b_counts = get_counts(specElement_b)
        livetime_bg = get_livetime(specElement_b)
        sumcounts = subtract_spectra(sumcounts, livetime_sum_s, specElement_b_counts, livetime_bg)

    sumcounts = numpy.array([0 if c < 0 else c for c in sumcounts])

    if all(sumcounts.astype(float) == sumcounts.astype(int)):
        # TODO: Make a switch to decide whether int or float
        countstxt = ' '.join(f'{round(count)}' for count in sumcounts)
    else:
        countstxt = ' '.join(f'{count:.4f}' for count in sumcounts)

    realtimes = ET.xpath(realtimeXPath)  # assumes realtime is a property of the radmeasurement
    realtime_sum_s = sum([Rf.ConvertDurationToSeconds(realtime.text) for realtime in realtimes])  # usually there's only one realtime
    realtime_sum_txt = Rf.ConvertSecondsToIsoDuration(realtime_sum_s)
    livetime_sum_txt = Rf.ConvertSecondsToIsoDuration(livetime_sum_s)

    RASE_sensitivity, FLUX_sensitivity = sensitivity_text(sumcounts, livetime_sum_s, uSievertsph, fluxValue)

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

    makotemplate = Template(text=base_template, input_encoding='utf-8')
    output = makotemplate.render(spectrum=countstxt, realtime=realtime_sum_txt, livetime=livetime_sum_txt,
                                 ecal=template_ecal, secondaries=secondaries,
                                 additional=additional, RASE_sens=RASE_sensitivity, FLUX_sens=FLUX_sensitivity)
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


def do_all(inputfile, config: dict, outputfolder, manufacturer, model, source, subtraction,
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
    try:
        subtraction_ET = get_ET_from_file(subtraction)
    except TypeError:
        subtraction_ET = subtraction

    output = build_base_ET(ET=ET, measureXPath=config['measurement_spectrum_xpath'],
                           realtimeXPath=config['realtime_xpath'], livetimeXPath=config['livetime_xpath'],
                           subtraction_ET=subtraction_ET, subtractionXpath=config.get('subtraction_spectrum_xpath'),
                           additionals=config.get('additionals'), secondaries_dict=config.get('secondaries'),
                           uSievertsph=uSievertsph, fluxValue=fluxValue, transform=transform,
                           ndetectors=int(config.get('ndetectors')), additional_meas=config['additional_meas'],
                           additional_liv=config['additional_liv']
                           )
    outputfilename = base_output_filename(manufacturer, model, source, description)
    write_base_text(output, outputfolder, outputfilename)



def add_bases(ET:etree.ElementTree, ET2: Union[etree.ElementTree,None], measureXPath=None, rtpath=None, calpath=None,
              additional_meas=None, additional_cal=None, ecal_baselines=None):
    """
    Sum up, spectrum by spectrum, for each detector (if multiple detectors in an instrument), across all
    spectrum files in a folder
    """
    measpaths = [measureXPath] + additional_meas if type(additional_meas) == list else [measureXPath]
    calpaths = [calpath] + additional_cal if type(additional_cal) == list else [calpath]
    ecals_arr = []
    for i, cal in enumerate(calpaths):
        try:
            if '@id="FromSpectrum"' in cal:
                ecalrefmeas = ET.xpath(measpaths[i])
                if len(ecalrefmeas) > 1:
                    ecalrefmeas = ecalrefmeas[0]
                ecaltag = ecalrefmeas.attrib['energyCalibrationReference']
                calpaths[i] = calpaths[i].replace("FromSpectrum", ecaltag)
                cal = calpaths[i]
            ecals = ET.xpath(cal)[0].text
        except (TypeError, etree.XPathError):
            ecals = cal
        except (AttributeError):
            ecals = str(ET.xpath(cal))
        except (IndexError):
            raise ValueError("Calibration XPath does not resolve to any element in input XML. "
                             "Please check base building config file and compare to the input XML.")
        ecalvals = [float(e) for e in ecals.split()]
        ecalvals += [0.] * (4 - len(ecalvals))
        ecals_arr.append(ecalvals)
    if ecal_baselines is None:
        ecal_baselines = ecals_arr

    if ET2: #if ET2 is None, just return ET
        old_energies = []
        for mpath, ecal in zip(measpaths, ecals_arr):  # just do this once
            m = ET.xpath(mpath)[0]
            old_energies.append(numpy.polyval(numpy.flip(ecal), numpy.arange(len(get_counts(m)) + 1)))
        for mpath, old_e, ecal_baseline in zip(measpaths, old_energies, ecal_baselines):
            for spec1, spec2 in zip(ET.xpath(mpath), ET2.xpath(mpath)):
                # recalibrate and add spectra
                counts1 = rebin(get_counts(spec1), old_e, ecal_baseline)   # to be rebinned to baseline
                counts2 = get_counts(spec2)  # this is the summed spectrum, already rebinned to baseline as necessary
                sum_counts = counts1 + counts2
                # add livetimes
                sum_livetime = get_livetime(spec1) + get_livetime(spec2) # we assume the livetime configuration is the same in the summed and to-be-summed specs
                insert_counts(spec1, sum_counts)
                reading.requiredElement(['LiveTime', 'LiveTimeDuration'], spec1).text = f'PT{sum_livetime}S' #set livetime in units of seconds only.
        #add realtimes
        for rt1, rt2 in zip(ET.xpath(rtpath), ET2.xpath(rtpath)):
            sum_rt = Rf.ConvertDurationToSeconds(rt1.text)+Rf.ConvertDurationToSeconds(rt2.text)
            rt1.text = f'PT{sum_rt}S'
        indent(ET.getroot())

    return ET, ecal_baselines


def do_list(inputfiles, config:dict, outputfolder, manufacturer, model, source, subtraction,
           uSievertsph=None, fluxValue=None, description=None, transform=None, master_ecal=None):
    comboET = None
    ecal_baselines = None
    try:
        subtraction_ET = get_ET_from_file(subtraction)
    except TypeError:
        subtraction_ET = subtraction
    for inputfile in inputfiles:
        ET_orig = get_ET_from_file(inputfile)
        comboET, ecal_baselines = add_bases(ET_orig, comboET, measureXPath=config['measurement_spectrum_xpath'],
                                   rtpath=config['realtime_xpath'], calpath=config['calibration'],
                                   additional_meas=config['additional_meas'], additional_cal=config['additional_cal'],
                                   ecal_baselines=ecal_baselines)
        if master_ecal is None:
            master_ecal = ecal_baselines
    outputfilename = base_output_filename(manufacturer, model, source, description)
    outET = build_base_ET(ET=comboET, measureXPath=config['measurement_spectrum_xpath'], realtimeXPath=config['realtime_xpath'],
                          livetimeXPath=config['livetime_xpath'], subtraction_ET=subtraction_ET,
                          subtractionXpath=config.get('subtraction_spectrum_xpath'), additionals=config.get('additionals'),
                          secondaries_dict=config.get('secondaries'), uSievertsph=uSievertsph, fluxValue=fluxValue,
                          transform=transform, ndetectors=int(config.get('ndetectors')),
                          additional_meas=config['additional_meas'],  additional_liv=config['additional_liv'],
                          ecal_baselines=ecal_baselines, master_ecal=master_ecal)
    write_base_ET(etree.ElementTree(etree.fromstring(bytes(outET, encoding='utf-8'))), outputfolder, outputfilename)
    return master_ecal


def do_glob(inputfileglob, config: dict, outputfolder, manufacturer, model, source, subtraction,
           uSievertsph=None, fluxValue=None, description=None, transform=None, master_ecal=None):
    inputfiles = glob(inputfileglob)
    master_ecal = do_list(inputfiles, config, outputfolder, manufacturer, model, source, subtraction,
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