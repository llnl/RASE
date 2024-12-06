#!/usr/bin/env python3
import sys, os
import requests
import argparse
import xml.etree.ElementTree as ET
"""
Query the ID algorithm for the GammaReality LAMP via the API endpoint

--- Request ---
POST /api/isotope_detect HTTP/1.1
Host: lamp.local
Content-Type: application/x-www-form-urlencoded

[Request Body - Spectrum JSON Payload]
---------------

The spectrum payload is a JSON string with two fields:
    E_bins: bin edges of spectrum including left and right edges in keV (length N+1)
    counts: counts in each bin (length N) 

It is recommended to use a 1 keV energy bin width for the spectrum payload
Input spectrum goes only up to 2000 keV
"""

# To generate a windows executable version:
# python -m PyInstaller -a -y -F --clean --noupx --distpath ..\dist --workpath ..\build LAMP_ID.py

def indent(elem, level=0):
    '''
    copy and paste from http://effbot.org/zone/element-lib.htm#prettyprint
    it basically walks your tree and adds spaces and newlines so the tree is
    printed in a nice way
    '''

    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def generate_id_report(identifications):
    id_report = ET.Element('IdentificationResults')
    for id_iso, id_conf in identifications:
        id_result = ET.SubElement(id_report, 'Identification')
        id_name = ET.SubElement(id_result, 'IDName')
        id_name.text = id_iso
        id_confidence = ET.SubElement(id_result, 'IDConfidence')
        id_confidence.text = id_conf
    indent(id_report)
    return id_report


def get_file_list(in_folder):
    return [f for f in os.listdir(in_folder) if f.endswith(".json")]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='LAMP_ID', description='LAMP Isotope ID via API Endpoint')
    parser.add_argument('inputdir', help='input folder')
    parser.add_argument('outputdir', help='output folder')
    parser.add_argument('hostname', nargs='?', help='LAMP endpoint hostname', default='lamp.local')
    a = parser.parse_args()

    for ff in get_file_list(a.inputdir):
        with open(os.path.join(a.inputdir, ff)) as f:
            spectrum_payload = f.read()

        try:
            r = requests.post(f'http://{a.hostname}/api/isotope_detect', data={'spectrum': spectrum_payload})
        except Exception as e:
            print(e)
            sys.exit(-1)

        ids = [(i, '1') for i in r.json()['isotopes']]
        if not ids:  # no identifications
            ids = [('', '0')]
        id_report = generate_id_report(ids)
        ET.ElementTree(id_report).write(os.path.join(a.outputFolder, ff.replace(".json", ".res")),
                                        encoding='utf-8', xml_declaration=True, method='xml')
