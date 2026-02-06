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
This module defines key functions used in RASE
"""
import csv
import glob
import io
import logging
import os
import re
import shutil
import bisect

from dataclasses import dataclass

from lxml import etree
from pathlib import Path
import isodate, datetime
import numpy as np
from mako import exceptions
from sqlalchemy.engine import create_engine, Engine
from sqlalchemy import event
from typing import List, Optional

from PySide6.QtCore import QCoreApplication
from src.rase_settings import APPLICATION_PATH, RASE_VERSION
from src.rebin import rebin
from src.scenarios_io import ScenariosIO
from src.table_def import BaseSpectrum, Detector, Scenario, \
    SampleSpectraSeed, Session, Base, ScenarioMaterial, ScenarioBackgroundMaterial, Material, \
    Replay, ScenarioGroup
from src.utils import compress_counts, indent

# translation_tag = 'funcs'
# configure the logger

# TODO: Remember to update the version number at each release!
logFile = os.path.join(APPLICATION_PATH, "rase.log")
FORMAT = '%(asctime)-15s RASE' + RASE_VERSION + ' %(levelname)s %(message)s'
logging.basicConfig(filename=logFile, level=logging.DEBUG, format=FORMAT)
# Add a console handler to also print to screen
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Set the logging level for the console
console_handler.setFormatter(logging.Formatter(FORMAT))  # Use the same format

# Add the console handler to the root logger
logging.getLogger().addHandler(console_handler)
# Key variables used in several places
secondary_type = {'base_spec': 0, 'scenario': 1, 'file': 2, 'None': None}

# Allowed results extensions
allowed_results_file_exts = (".n42", ".res", ".csv", ".xml", ".txt", ".json")


def initializeDatabase(databaseFilepath):
    """
    binds Session to database and creates new database if none exists

    :param databaseFilepath: path to src.sqlite file
    """

    if Session.bind is None: #do not create engine if it already exists; this is important for tests which initialize the DB during tests and then sometimes do it again when opening a main RASE dialog
        engine = create_engine('sqlite:///' + databaseFilepath)
        Session.remove() #need to remove existing session created when we checked the bind above, or the old session will persist with no bind.
        Session.configure(bind=engine)

    if not os.path.exists(databaseFilepath):
        Base.metadata.create_all(Session.bind)
        return False
    return True


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def importDistortionFile(filepath):
    """
    Import Influences from distorsion (.dis) xml file formatted as in old RASE
    :param filepath: path of valid influence file
    :return: array of influence names and corresponding distorsion values
    """
    root = etree.parse(filepath).getroot()
    detInfluences = []
    for inflElement in root:
        inflName = inflElement.tag
        inflVals = [float(value) for value in inflElement.find('Nonlinearity').text.split()]
        detInfluences.append((inflName, inflVals))
    return detInfluences


def ConvertDurationToSeconds(inTime):
    """
    converts text string to seconds
    :param inTime: text string in ISO format ("PTxxx")
    :return: duration in seconds
    """
    try:
        outTime = isodate.parse_duration(inTime)
    except:
        outTime = isodate.parse_duration('PT'+inTime+'S')
    return outTime.total_seconds()


def ConvertSecondsToIsoDuration(inseconds):
    """
    converts seconds to text string
    :param inseconds: seconds
    :return: ISO "PT" textstring
    """
    dt = datetime.timedelta(seconds=inseconds)
    return isodate.duration_isoformat(dt)


class ResultsFileFormatException(Exception):
    pass


def process_confidences(confidences: list, results: list, use_confs: bool, confidence_map=
                                        Replay.confidence_scale_default_map, confidence_range=
                                        Replay.confidence_scale_default_range) -> list:
    """
    Updates confidence handling. A provided map or range will be used to interpret the values in the file on a scale of 0-1.
    """
    converted = [1] * len(results)
    if use_confs and confidences:
        # for some instruments (e.g.: RadEagle), the confidences are zeros while the isotopes are dashes
        if len(confidences) > len(results):
            confidences = confidences[0:len(results)]
        if confidences:
            try:
                converted = [confidence_map[c] for c in confidences]
            except KeyError:
                try:
                    converted = [np.interp(c,confidence_range[0],confidence_range[1]) for c in confidences]
                except:
                    logging.info('At least one reported confidence is non-numeric or in the user confidence map. Defaulting to 1.')
            confidences = converted
    return converted


def H3D_results_parser(filename: str or os.PathLike, use_confs=True, confidence_scale_range=[[0,100],[0,1]]):
    """
    Parse H3D replay tool results output which is a 3-column tab-separated text file with 1 header line.
    The three columns are: IsotopeName, Confidence, Uncertainty
    Confidence is a value in [0 - 100]
    """
    with open(filename) as f:
        cells = list(csv.reader(f, delimiter='\t'))
    results = [r[0] for r in cells[1:]]
    confidences = process_confidences([float(r[1]) for r in cells[1:]],
                                      results, use_confs, confidence_range=confidence_scale_range)
    return results, confidences


def DetectiveX_results_parser(filename: str or os.PathLike, use_confs=True, confidence_scale_range=[[0,100],[0,1]]):
    """
    Parse DetectiveX replay tool results output which is in json format.
    """
    import json
    with open(filename) as f:
        data = json.load(f)
    ids = data[0]['Results']['IdentifiedNuclides']
    results = [id['Name'] for id in ids]
    confidences = process_confidences([id['ProbabilityPresentInSpectrum'] for id in ids],
                                      results, use_confs, confidence_range=confidence_scale_range)
    return results, confidences

def readTranslatedResultFile(filename, use_confs, replay):
    """
    Reads translated results file from defaults formats

    Format 1 (RASE defined):
    //IdentificationResults
		/Isotopes (single)
			/text(): \n-separated list of identification labels
		/ConfidenceIndex (single)
			/text(): \n-separated list of confidence indices

	Format 2 (RASE defined):
	//IdentificationResults
	    /Identification (multiple)
    	    /IDName
	            /text(): nuclide label
	        /IDConfidence
	            /text(): confidence level

    Format 3 (BARNI):
    // NuclideResult
        /Nuclide
        /Score

    Format 4 (n42-2011)
    Used by:
     - most FLIR except R440
     - CAEN DiscoveRAD
     - Symetrica SN33

    Format 5 (ICD2/HPRDS)
    Used by:
     - Smiths RadSeeker
     - ORTEC HPGe replay tool (standalone version)

     Format 6 (CSV)
     Used by: Kromek D5 - PCS Offline v170.1.5.7
     it processes only the first line since we expect 1 spectrum per file

    :param filename: path of valid results file
    :param use_confs: when set confidences are mapped to 'low', 'medium', 'high' values
    :return: list of identification results
    """
    if os.path.getsize(os.path.join(str(filename))) == 0:
        return [], []

    if str(filename).endswith(".txt"):
        return H3D_results_parser(filename, use_confs, replay.confidence_scale_range)

    if str(filename).endswith(".json"):
        return DetectiveX_results_parser(filename, use_confs, replay.confidence_scale_range)

    # Parse CSV format (Kromek D5 PCS Offline or BNC SAM940)
    # Label1, Label2, Integration time, Messages(i.e.errors), Result1 confidence, Result1 isotope, Result2 confidence, Result2 isotope, ...
    if str(filename).endswith(".csv"):
        with open(filename) as f:
            header = f.readline()  # skip header line
            line = f.readline()
            if [s.strip() for s in header.split(',')][0] == 'EventNumber':  # BNC SAM940
                if line == '':
                    raw_results = ['']
                else:
                    raw_results = [s.strip() for s in line.split(',')][-2].split(' ')
                if raw_results != ['']:
                    raw_results.reverse()
                    raw_results[::2] = [str(float(s.replace('%', '')) / 100) for s in raw_results[::2]]
            else:
                raw_results = [s.strip() for s in line.split(',')[4:]]
        results = raw_results[1::2]
        confidences = process_confidences(raw_results[0::2], results, use_confs, replay.confidence_scale_map, replay.confidence_scale_range)
        return results, confidences

    root = etree.parse(str(filename)).getroot()
    if ((root.tag != "IdentificationResults")   # RASE Format 1, 2
            and (root.tag != "NuclideResultList")  # BARNI
            and not (root.tag.endswith("RadInstrumentData"))  # n42-2011
            and (root.tag != 'Event')):  # ICD2/HPRDS
        raise ResultsFileFormatException(f'{filename}: bad file format')

    confidences = []
    results = []
    if root.tag == "IdentificationResults":
        # Parse RASE format 1
        if len(root.findall('Isotopes')) > 0:
            isotopes = root.find('Isotopes').text
            if isotopes:
                results = [stripped for x in isotopes.split('\n') if (stripped := x.strip()) not in {'-', ''}]
                confidences_str = ''
                if root.find('ConfidenceIndex') is not None:
                    confidences_str = root.find('ConfidenceIndex').text
                elif root.find('Confidences') is not None:
                    confidences_str = root.find('Confidences').text
                if confidences_str:
                    confidences = [stripped for x in confidences_str.split('\n') if (stripped := x.strip()) not in {'-', ''}]
        # Parse RASE format 1.5 (MicroDetective; lists all IDs/confidences in one block separated by spaces)
        elif len(root.findall('Isotope')) > 0:
            isotopes = root.find('Isotope').text
            if isotopes:
                # split all identifications using regex
                results = [m.strip() for mm in re.findall(r'"([^"]*)"|( [^"]\S*)|(^[^"]\S*)', isotopes) for m in mm if m]
            confidenceValue = root.find('ConfidenceIndex')
            if confidenceValue is not None:
                confidences = confidenceValue.text.split()
        # Parse RASE Format 2
        elif len(root.findall('Identification')) > 0:
            for identification in root.findall('Identification'):
                idname = identification.find('IDName')
                if idname.text:
                    results.append(idname.text.strip())
                    confidences.append(identification.find('IDConfidence').text.strip())
                else:
                    confidences.append('')
    # Parse BARNI output format
    elif len(root.findall('NuclideResult')) > 0:
        for identification in root.findall('NuclideResult'):
            idname = identification.find('nuclide')
            if idname.text:
                results.append(idname.text.strip())
                confidences.append(identification.find('score').text.strip())
            else:
                confidences.append('')
    # Parse n42-2011 format
    # For simplicity '{*}' is used to accept all namespaces
    elif root.tag.endswith("RadInstrumentData"):
        if root.find('.//{*}NuclideAnalysisResults') is not None:
            for element in root.findall('.//{*}Nuclide'):
                results.append(element.find('{*}NuclideName').text)
                confidences.append(element.find('{*}NuclideIDConfidenceValue').text)
    # Parse ICD2/HPRDS
    elif len(root.findall('AnalysisResults')):
        for nuclide in root.iter('Nuclide'):
            results.append(nuclide.find('NuclideName').text)
            confidences.append(nuclide.find('NuclideIDConfidence').text)
    else:
        raise ResultsFileFormatException(f'{filename}: bad file format')

    confidences = process_confidences(confidences, results, use_confs, replay.confidence_scale_map, replay.confidence_scale_range)
    return results, confidences


def uncompressCountedZeroes(chanData,counts):
    if (chanData.attrib.get('Compression') == 'CountedZeroes') or (
            chanData.attrib.get('compressionCode') == 'CountedZeroes'):
        uncompressedCounts = []
        countsIter = iter(counts)
        for count in countsIter:
            if count == float(0):
                uncompressedCounts.extend([0] * int(next(countsIter)))
            else:
                uncompressedCounts.append(count)
        counts = ','.join(map(str, uncompressedCounts))
    else:
        counts = ','.join(map(str, counts))
    return counts


def strip_namespaces(tree:etree.ElementTree):
    # xpath query for selecting all element nodes in namespace
    tree.getroot()
    query = "descendant-or-self::*[namespace-uri()!='']"
    # for each element returned by the above xpath query...
    for element in tree.xpath(query):
        # replace element name with its local name
        element.tag = etree.QName(element).localname
    tree.getroot().attrib.clear()
    etree.cleanup_namespaces(tree)
    return tree


def remove_control_characters(xml):
    def str_to_int(s, default, base=10):
        if int(s, base) < 0x10000:
            return chr(int(s, base))
        return default

    xml = re.sub(r"&#(\d+);?", lambda c: str_to_int(c.group(1), c.group(0)), xml)
    xml = re.sub(r"&#[xX]([0-9a-fA-F]+);?", lambda c: str_to_int(c.group(1), c.group(0), base=16), xml)
    xml = re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", xml)
    return xml


def get_ET_from_file(inputfile):
    try:
        et = parse_ET(inputfile, 'utf-8')
    except:
        et = parse_ET(inputfile, 'utf-8-sig')
    return et


def parse_ET(inputfile, encoding='utf-8'):
    with open(inputfile, 'r', encoding=encoding) as inputf:
        inputstr = inputf.read()
        inputstr = remove_control_characters(inputstr)
        parser = etree.XMLParser(recover=True)
        inputstr_io = io.BytesIO(bytes(inputstr, encoding=encoding))
        et = etree.parse(inputstr_io, parser)
        strip_namespaces(et)
    return et


def getSeconds(text):
    """
    translates file time format into seconds
    :param text: input time format
    :return: seconds as string
    """
    text = text.lower().strip('pts')
    seconds = 0
    if not text == "" and 'h' in text:
        hours, text = text.split('h')
        seconds += int(hours) * 3600
    if not text == "" and 'm' in text:
        minutes, text = text.split('m')
        seconds += int(minutes) * 60
    if not text == "":
        seconds += float(text)
    return seconds

def rebin_ecal_disagreement(newEcal, oldEcal, chancount, counts):
    if not (np.array_equal(newEcal, oldEcal)):
        oldenergies = np.polyval(np.flip(oldEcal), np.arange(chancount))
        return rebin(counts, oldenergies, newEcal)
    else:
        return counts

def create_n42_file(filename, scenario, detector, sample_counts, secondary_spectrum=None, neutrons=0):
    """
    Creates n42 file from input
    :param filename: path of resultant n42 file
    :param scenario: scenario info
    :param detector: detector info
    :param sample_counts: sample counts array
    :param secondary_spectrum: optional secondary spectrum array
    """
    # FIXME: should use ElementTree instead of manually creating the XML text
    f = open(filename, 'w')
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<N42InstrumentData>\n')
    f.write('  <Measurement>\n')
    f.write('    <Spectrum>\n')
    f.write('      <SourceType>Item</SourceType>\n')
    f.write('      <MeasurementClassCode>Foreground</MeasurementClassCode>\n')
    f.write('      <RealTime Unit="sec">PT{}S</RealTime>\n'.format(scenario.acq_time))
    f.write('      <LiveTime Unit="sec">PT{}S</LiveTime>\n'.format(scenario.acq_time))
    f.write('      <Calibration Type="Energy" EnergyUnits="keV">\n')
    f.write('        <Equation Model="Polynomial">\n')
    f.write('          <Coefficients>{} {} {} {}</Coefficients>\n'.format(detector.ecal0, detector.ecal1, detector.ecal2, detector.ecal3))
    f.write('        </Equation>\n')
    f.write('      </Calibration>\n')
    f.write('      <ChannelData>')
    if all([float(k) == int(k) for k in sample_counts]):
        f.write('{}'.format(' '.join('{:d}'.format(x) for x in sample_counts)))
    else:
        f.write('{}'.format(' '.join('{:f}'.format(x) for x in sample_counts)))
    f.write('</ChannelData>\n')
    f.write('    </Spectrum>\n')
    #neutrons
    f.write(f'''    <GrossCounts id="NeutronForeground">
        <LiveTimeDuration>PT{scenario.acq_time}S</LiveTimeDuration>
        <CountData>{neutrons}</CountData>
    </GrossCounts>
''')
    if secondary_spectrum:
        if (detector.secondary_type == secondary_type['scenario']):
            type_str = 'Background'
        elif (detector.sample_intrinsic and len(detector.secondary_spectra) == 1) or \
                detector.secondary_classcode == 'Calibration':
            type_str = 'Calibration'
        else:
            type_str = detector.secondary_classcode #'Background'
        f.write('    <Spectrum>\n')
        f.write(f'      <MeasurementClassCode>{type_str}</MeasurementClassCode>\n')
        f.write('      <RealTime Unit="sec">PT{}S</RealTime>\n'.format(secondary_spectrum.realtime))
        f.write('      <LiveTime Unit="sec">PT{}S</LiveTime>\n'.format(secondary_spectrum.livetime))
        f.write('      <Calibration Type="Energy" EnergyUnits="keV">\n')
        f.write('        <Equation Model="Polynomial">\n')
        f.write('          <Coefficients>{} {} {} {}</Coefficients>\n'.format(detector.ecal0, detector.ecal1,
                                                                              detector.ecal2, detector.ecal3))
        f.write('        </Equation>\n')
        f.write('      </Calibration>\n')
        f.write('      <ChannelData>')
        f.write(secondary_spectrum.get_counts_as_str())

        f.write('</ChannelData>\n')
        f.write('    </Spectrum>\n')
        #background neutrons
        f.write(f'''    <GrossCounts id="NeutronBackground">
        <LiveTimeDuration>PT{secondary_spectrum.livetime}S</LiveTimeDuration>
        <CountData>{secondary_spectrum.neutrons}</CountData>
    </GrossCounts>
''')
    f.write('  </Measurement>\n')
    f.write('</N42InstrumentData>\n')
    f.close()


def create_n42_file_from_template(n42_mako_template, filename, scenario, detector, sample_counts : np.ndarray, secondary_spectrum=None, neutrons=None):
    """
    Creates n42 file from input using teplate
    :param n42_mako_template: template used to make file
    :param filename: path of resultant n42 file
    :param scenario: scenario info
    :param detector: detector info
    :param sample_counts: sample counts array
    :param secondary_spectrum: optional secondary spectrum array
    """
    template_data = dict(
        scenario=scenario,
        detector=detector,
        # TODO: we may want to create a 'sample_counts' class with methods to return it in different formatting

    )
    try:
        template_data['sample_counts'] = ' '.join('{:d}'.format(x) for x in sample_counts)
        template_data['compressed_sample_counts'] = ' '.join('{:d}'.format(x) for x in compress_counts(sample_counts))
        template_data['sample_counts_array'] = sample_counts
        template_data['bin_edges'] = ' '.join(str(v) for v in np.polyval([detector.ecal3, detector.ecal2, detector.ecal1, detector.ecal0], np.arange(detector.chan_count+1)))
    except TypeError: # used for DRASE only.
        template_data['sample_periods'] = sample_counts

    if secondary_spectrum:
        secondary_spectrum.counts = secondary_spectrum.counts.astype(int)
        template_data.update(dict(secondary_spectrum=secondary_spectrum))

    if neutrons:
        template_data['neutrons'] = neutrons

    try:
        templated_content = n42_mako_template.render(**template_data)
    except:
        logging.info(QCoreApplication.translate('funcs', 'Mako Template exception:'))
        err_msg = exceptions.text_error_template().render()
        logging.info(err_msg)
        print(err_msg)
        raise

    with open(filename, 'w', newline='') as f:
        f.write(templated_content)


def write_results(results_array, out_filepath):
    """
    Write a RASE-formatted results file from results data
    :param results_array: list of (isotope, confidence level) tuples
    :param out_filepath: full pathname of output file
    :return: None
    """
    root = etree.Element('IdentificationResults')

    if not results_array:
        results_array.append(('', 0))

    for iso, conf in results_array:
        identification = etree.SubElement(root, 'Identification')
        isotope = etree.SubElement(identification, 'IDName')
        isotope.text = iso
        confidence = etree.SubElement(identification, 'IDConfidence')
        confidence.text = conf

    indent(root)
    tree = etree.ElementTree(root)
    tree.write(out_filepath, encoding='utf-8', xml_declaration=True, method='xml')
    return


def strip_xml_tag(str):
    """
    Returns string stripped of XML tag
    """
    return re.sub('<[^<]+>', "", str)

##############################################
'''
# Helpers to build RASE output folder structure:
data_dir/
  detector1/
    scenario1/
      RASE-spectra/
      replay1/
        spectra/
        results/
      replay2/
        results/      
      replay3/
        spectra/
        results/
        translatedResults/
    scenario2/
      RASE-spectra/
      replay2/
        results/
      replay4/
        spectra/
        results/
  detector2/
    scenario1/
      RASE-spectra/
'''

def get_data_dir(data_root_dir: str | os.PathLike, detector: Detector, scenario_id: str) -> str:
    """
    Returns the base folder where all output data are stored for a given detector-scenario pair.
    """
    return str(Path(data_root_dir) / detector.id / scenario_id)


def get_sample_dir(data_root_dir, detector: Detector, scenario_id: str):
    """
    Returns the folder where the generated sample spectra are saved.
    """
    return str(Path(get_data_dir(data_root_dir, detector, scenario_id)) / 'RASE-spectra')


def get_replay_input_dir(data_root_dir, detector: Detector, replay: Optional[Replay], scenario_id: str):
    """
    Returns the folder where the sample spectra are saved in the format for the replay tool.
    If no replay template is configured, falls back to the RASE sample spectra folder.
    """
    data_dir = get_data_dir(data_root_dir, detector, scenario_id)
    if replay and replay.n42_template_path:
        return str(Path(data_dir) / replay.id / "spectra")
    return get_sample_dir(data_root_dir, detector, scenario_id)


def get_replay_output_dir(data_root_dir, detector: Detector, replay: Replay, scenario_id: str):
    """
    Returns the folder where the output of the replay tool is placed.
    """
    data_dir = get_data_dir(data_root_dir, detector, scenario_id)
    return str(Path(data_dir) / replay.id / "results")


def get_results_dir(data_root_dir, detector:Detector, replay: Replay, scenario_id: str) -> str:
    """
    Returns the name of the folder with the analyzed files (after replay) in RASE format
    If a translator is configured (translator_exe_path is not empty), returns '{replay.id}-translatedResults',
    """
    data_dir = get_data_dir(data_root_dir, detector, scenario_id)
    if replay.translator_exe_path:
        return str(Path(data_dir) / replay.id / "translatedResults")
    return get_replay_output_dir(data_root_dir, detector, replay, scenario_id)

##############################################


def get_sample_spectra_filename(detector_id: str, scenario_id: str, filenum: int, suffix=".n42"):
    return f"{detector_id}___{scenario_id}___{filenum}{suffix}"


def get_results_files(sample_root_dir: str | os.PathLike, detector: Detector, replay: Replay, scenario_id: str) -> list[str]:
    """
    Returns the list of results files. Allowed extensions are processed in order of precedence to handle the case
    of multitple results file types. Empty list is returned if no results files are found.
    """
    res_dir = get_results_dir(sample_root_dir, detector, replay, scenario_id)
    res_dir = Path(res_dir)
    fc_fileList = []
    if res_dir.exists() and res_dir.is_dir():
        for ext in allowed_results_file_exts:
            fc_fileList = [str(f) for f in Path(res_dir).glob(f"*{ext}")]
            if fc_fileList: break
    return fc_fileList


def files_endswith_exists(dir, endswith_filters):
    """
    Search if at least one file exists in 'dir' that ends with one of the specified filters
    :param dir: search path (folder)
    :param endswith_filters: tuple of file endings to filter e.g. (".n42",".res")
    :return: True if at least one file exists in path that match filter
    """
    if not os.path.exists(dir):
        return False
    for f in os.listdir(dir):
        if f.endswith(endswith_filters):
            return True
    return False


def count_files_endwith(dir, endswith_filters):
    """
    Search if any files exists in 'dir' that ends with one of the specified filters
    :param dir: search path (folder)
    :param endswith_filters: tuple of file endings to filter e.g. (".n42",".res")
    :return: Number of files that match the filter that exist in path
    """
    num_files = 0
    if not os.path.exists(dir):
        return 0
    for f in os.listdir(dir):
        if f.endswith(endswith_filters):
            num_files += 1
    return num_files


def find_scenario_dirs(root_dir: os.PathLike | str, scenario_id: str) -> List[Path]:
    root_path = Path(root_dir)
    # '**/scenario' finds all 'scenario' directories at any depth
    return [p for p in root_path.glob(f'**/{scenario_id}') if p.is_dir()]


def delete_scenarios(scenario_ids: List[str], sample_root_dir: os.PathLike | str):
    """
    Delete scenarios from database and cleanup sample folders
    """
    session = Session()
    for id in scenario_ids:
        scenDelete = session.query(Scenario).filter(Scenario.id == id)

        # folders
        folders = find_scenario_dirs(sample_root_dir, id)
        for folder in folders:
            shutil.rmtree(folder)

        # database
        scenObj = scenDelete.first()
        scenObj.scenario_groups.clear()
        scenObj.influences.clear()
        session.delete(scenObj)

        matDelete = session.query(ScenarioMaterial).filter(ScenarioMaterial.scenario_id == id)
        if matDelete.first():
            session.delete(matDelete.first())
        backgMatDelete = session.query(ScenarioBackgroundMaterial).filter(ScenarioBackgroundMaterial.scenario_id == id)
        if backgMatDelete.first():
            session.delete(backgMatDelete.first())

        session.commit()
    # session.close()


def delete_instrument(session, name):
    """Delete one instrument from database given its name"""
    sssDelete = session.query(SampleSpectraSeed).filter(SampleSpectraSeed.det_name == name)
    sssDelete.delete()
    detReplayDelete = session.query(Detector).filter(Detector.name == name).first()
    if detReplayDelete:
        detReplayDelete.influences.clear()
        detReplayDelete.replays.clear()
        session.delete(detReplayDelete)
    session.commit()


def delete_replay(session, replay_name:str):
    """Delete one instrument from database given its name"""
    replay = session.query(Replay).filter_by(name=replay_name).first()
    if replay:
        replay.detectors.clear()
        session.delete(replay)


def get_or_create_material(session, matname, include_intrinsic=False):
    material_name = Material.get_name(matname, include_intrinsic)
    material = session.query(Material).filter_by(name=material_name).first()
    if not material:
        material = Material(name=matname, include_intrinsic=include_intrinsic)
        session.commit()
    return material


def check_groups():
    """
    Make sure there is a default group (a group that cannot be deleted) for
    scenarios to exist in initially if they are not added to another at creation
    """
    session = Session()
    if not session.query(ScenarioGroup).filter_by(name='default_group').first():
        session.add(ScenarioGroup(name='default_group'))
        session.commit()


def export_scenarios(scenarios_ids, file_path):
    """
    Export scenarios from database to xml file
    """
    session = Session()
    scenarios = [session.query(Scenario).filter_by(id=scenid).first() for scenid in scenarios_ids]

    scen_io = ScenariosIO()
    xml_str = scen_io.scenario_export(scenarios)
    Path(file_path).write_text(xml_str)


def import_scenarios(file_path, file_format='xml', group_name=None, group_desc=None):
    """
    Import scenarios from an xml file into a list of scenarios. Objects are not committed to db here.
    """
    scen_io = ScenariosIO(group_name=group_name, group_desc=group_desc)
    if file_format == 'csv':
        # import is taken from a tree directly
        xml_str = scen_io.xmlstr_from_csv(file_path)
        return scen_io.scenario_import(xml_str)
    elif file_format == 'xml':
        # xml is taken from a file
        return scen_io.scenario_import(Path(file_path).read_text())
    else:
        return []


def calc_result_uncertainty(p, n, alpha=0.05):
    """
    http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
    Alpha confidence intervals for a binomial distribution of p expected successes on n trials using the Wilson Score
    approach. Wilson Score intervals are biased towards 0.5, and are asymmetric, but have been shown to have a more
    accurate performance than "exact" methods such as Clopper-Pearson, which tend to be overly conservative (see
    Newcombe, 1998). z-values are hard-coded for alpha = 0.01 (99%), 0.05 (95%), 0.1 (90%), and 0.32 (68%).
    """
    alpha_dict = {
        0.01: 2.576,
        0.05: 1.96,
        0.1: 1.645,
        0.32: 0.994,
    }

    # z = norm.ppf(1 - alpha / 2)
    # TODO: add alpha drop-down selection in some window (correspondence table?) to prevent alphas not in dictionary
    # from being entered
    z = alpha_dict[alpha]
    p_prime = (p + z ** 2 / (2 * n)) / (1 + z ** 2 / n)
    s_prime = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / (1 + z ** 2 / n)
    CI_pos = p_prime + s_prime
    CI_neg = p_prime - s_prime

    return CI_pos, CI_neg


def files_exist(directory, globadd='/*'):
    if os.path.exists(directory) and glob.glob(directory + globadd):
        return True
    return False


def apply_distortions(new_influences, counts, bin_widths, energies, ecal):
    count_bs = BaseSpectrum()
    if (not new_influences[0] == 0) or (not new_influences[2] == 0) or (not new_influences[1] == 1):
        counts = rebin(np.array(counts), energies, ecal)
    count_bs.counts = counts
    counts = gaussian_smearing(counts, bin_widths, new_influences[4], count_bs.is_spectrum_float())
    return counts


def calculate_influence(scenario, detector, degradations, ecal):
    session = Session()

    energies = np.polyval(np.flip(ecal), np.arange(detector.chan_count))
    new_influences = []
    bin_widths = np.zeros([len(scenario.influences), len(energies)])
    for index, influence in enumerate(scenario.influences):
        detInfl = influence.detector_influence
        new_infl = [detInfl.infl_0, detInfl.infl_1, detInfl.infl_2, detInfl.fixed_smear, detInfl.linear_smear]
        if degradations:
            new_infl = [infl + deg for infl, deg in zip(new_infl, degradations[index])]
            # deal with potential negative values
            for position, n_inf in enumerate(new_infl):
                if n_inf < 0:
                    if not position == 1:
                        new_infl[position] = 0
                    else:
                        new_infl[position] = 0.0001

        new_influences.append(new_infl)

        if new_infl[0] != 0 or new_infl[2] != 0 or new_infl[1] != 1:
            energies = np.polyval([new_infl[2], (new_infl[1]), new_infl[0]], energies)
        # convert fixed energy smear distortion from energy to bins
        if new_infl[3] != 0:
            e_width = new_infl[3] / 2
            for sub_index, energy in enumerate(energies):
                b0 = np.roots([new_infl[2], new_infl[1], new_infl[0] - (energy - e_width)])
                b1 = np.roots([new_infl[2], new_infl[1], new_infl[0] - (energy + e_width)])
                bin_widths[index][sub_index] = max(b1) - max(b0)
    return new_influences, bin_widths, energies


def gaussian_smearing(orig_hist, bin_widths, res_percent, is_float=False):
    #TODO: Temp fix to make gaussian smearing fast by forcing integers in influence scenarios
    is_float = False
    if is_float:
        order_of_mag_list = [round(np.log10(v)) for v in orig_hist if v > 0]  # to prevent scaling values to large
                                                                              # values that make sampling take forever
        if min(order_of_mag_list) < 0:
            oom_scale = int(np.power(10, (min(order_of_mag_list) + 1) * -1))
        else:
            oom_scale = int(np.power(10, max((4 - max(order_of_mag_list)), 0)))
        hist = np.array(orig_hist * oom_scale).astype(int)
    else:
        hist = orig_hist  # expect counts, so casting into int
    sigma = (res_percent / 100) / 2.355

    # gaussian smearing
    a = [np.random.normal(i, b + sigma * i, int(k)) for i, (b, k) in enumerate(zip(bin_widths, hist))]
    a = np.concatenate(a)

    # reformat into an histogram
    smeared_hist, __ = np.histogram(a, bins=np.arange(0, len(orig_hist) + 1))

    if is_float:
        smeared_hist = smeared_hist / oom_scale

    return smeared_hist

def find_nearest_inlist(thicknesses: list, goal_thickness: float) -> list:
    """
    Given a list of numbers and a value, finds the numbers in the list closest to the value.
    If out of bounds, gives the two highest or lowest in the list.
    If exactly a number in the list, returns a list of length 1.
    :param thicknesses: list of floats (usually in units of cm)
    :param goal_thickness: float (same units as thicknesses) indicating the shielding thickness we want
    :return:
    """
    keys = sorted(thicknesses)
    idx = bisect.bisect_left(keys, goal_thickness)
    if idx < len(keys) and keys[idx] == goal_thickness:  # value is exactly a value in the list
        return [goal_thickness]
    elif idx == 0:  # value is less than the smallest key
        return [keys[0], keys[1]]
    elif idx == len(keys):  # value is greater than the largest key
        return [keys[-2], keys[-1]]
    else:  # value is between two keys
        return [keys[idx-1], keys[idx]]





def remove_xmlblock(in_dir: str | os.PathLike, out_dir: str | os.PathLike, removal_tag: str='AnalysisResults',
                    copy_unmodified: bool=True, additional_suffixes: Optional[List[str]]=None,
                    log_noanalysis_files: bool=True) -> List[int]:
    """
    Removes data formatted with a given tag. By default, this is used for AnalysisResults, but
    can in principle be used to remove any blocks. Looks for all .n42/.N42 and .xml/.XML files
    :param in_dir: Path object (or string), the path where the input spectra are located
    :param out_dir: Path object (or string), the path where the output spectra are located
    :param removal_tag: string, The tag to be removed from the .n42/.xml file
    :param copy_unmodified: bool, write all files to output directory regardless of if there were results
                            in the original file to be removed or not
    :param additional_suffixes: list, include file suffixes that are beyond the default (*.n42, *.N42, *.xml, *.XML)
    :param log_noanalysis_files: bool, write a text file in the output dir noting which files did not have their
                          results removed (includes files without results)
    :return: A list containing two integers: [n_converted, n_copied].
    """
    in_dir = Path(in_dir)  # in case input is string (API implementation)
    out_dir = Path(out_dir)
    Path(out_dir / f'{removal_tag}_not_present.txt').unlink(missing_ok=True)

    if not in_dir.is_dir():
        raise FileNotFoundError(QCoreApplication.translate('funcs', 'Input dir does not exist. '
                                                                    'Select a directory that exists.'))

    patterns = ['*.n42', '*.N42', '*.xml', '*.XML']  # deal with cases
    if additional_suffixes:
        patterns += additional_suffixes
    # Windows doesn't distinguish between caps/non-caps, macos does. So we have to avoid those duplicates on Windows
    matching_files = list(set(k for p in patterns for k in in_dir.rglob(p) if k.is_file()))

    n_converted = 0  # track files for output message
    n_copied = 0
    for filename in matching_files:
        relative_path = filename.relative_to(in_dir)  # maintain relative directory structure for nested directories
        target_path = out_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            tree = etree.parse(filename)
        except etree.XMLSyntaxError: # possible causes could be settings files, for example
            logging.info(QCoreApplication.translate('funcs',
                          'Could not parse {} due to file incompatibility\n (possible causes include non-spectra '
                          '.n42/.xml files, and is not necessarily a problem.'.format(filename)))
            if copy_unmodified:  # copy over those files anyways
                shutil.copy(filename, target_path)
                n_copied += 1
            continue

        root = tree.getroot()
        results_block = root.find('{*}'+f'{removal_tag}')
        if results_block is not None:
            root.remove(results_block)
            tree.write(out_dir / target_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
            n_converted += 1
        else:
            if log_noanalysis_files:
                with open(out_dir / f'{removal_tag}_not_present.txt', 'a') as f:
                    f.write(str(relative_path) + '\n')
            if copy_unmodified:
                n_copied += 1
                tree.write(out_dir / relative_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    return n_converted, n_copied
