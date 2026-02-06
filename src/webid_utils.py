###############################################################################
# Copyright (c) 2018-2026 Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
#
# Written by J. Brodsky, J. Chavez, S. Czyz, G. Kosinovsky, V. Mozin,
#           S. Sangiorgio.
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
# WebID utilities
import os
import re
import io
import json
import logging
import requests
from requests import Response
from pathlib import Path
from lxml import etree
from src.utils import indent

# Compiled bytes regex (fast, robust)
xml_model_pattern_bytes = re.compile(rb'<\?xml-model\b.*?\?>\s*', flags=re.DOTALL | re.IGNORECASE)

def remove_xml_model(xml_file: str | Path) -> io.BytesIO:
    """
    Remove all <?xml-model ...?> processing instructions from the XML bytes and
    return a BytesIO stream.
    """
    # Read raw bytes to avoid decoding issues across encodings
    with open(xml_file, "rb") as f:
        content = f.read()

    # Remove PI occurrences anywhere in the file
    cleaned = xml_model_pattern_bytes.sub(b'', content)

    # Return as file-like stream (cursor at position 0)
    return io.BytesIO(cleaned)


def response_is_json(r: Response) -> bool:
    """
    Check that the response is JSON.
    """
    if 'application/json' not in r.headers.get('Content-Type', ''):
        logging.error("Non-JSON response from server: %s", r.text[:500])
        return False
    return True


def webid_response_is_success(r: Response) -> bool:
    """
    Check if the analysis from Full Spectrum was successful based on JSON payload.
    """
    if not response_is_json(r):
        return False
    else:
        data = r.json()
        if any(data.get(k, 0) != 0 for k in ['code', 'analysisError', 'initializationError']):
            logging.error('Error Message: %s', data.get('errorMessage', 'Unknown error'))
            return False
        return True


def get_ids_from_webid(inputdir, outputdir, drf, url='https://full-spectrum.sandia.gov/', bkg_file=None, synthesize_bkg=False):
    """
    Send .n42 files to the WebID API and write identification results to output files.

    :param inputdir: Path to directory containing .n42 input files.
    :param outputdir: Path to directory where .res files will be written.
    :param drf: Detector response function identifier.
    :param url: Base URL of the WebID API.
    :param bkg_file: Optional background file path.
    :param synthesize_bkg: Whether to synthesize background.
    :raises Exception: If an API request fails.
    :returns: None
    """
    api_url = url.strip().strip('/') + "/api/v1/analysis"
    session = requests.Session()

    for ff in [f for f in os.listdir(inputdir) if f.endswith(".n42")]:
        # Strip <?xml-model ...?> instructions for security: WebID server rejects xml-model PIs
        ipc_path = os.path.join(inputdir, ff)
        ipc_stream = remove_xml_model(ipc_path)
        files = {"ipc": ipc_stream}
        # prepare optional background stream
        if bkg_file:
            bkg_stream = remove_xml_model(bkg_file)
            files["back"] = bkg_stream

        payload = {"options": json.dumps({'synthesizeBackground': synthesize_bkg, 'drf': drf})}

        try:
            r = session.post(f'{api_url}', files=files, data=payload)
            # Ensure HTTP errors raise exceptions
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Network issue or HTTP error
            logging.error("WebID API request failed: %s", e)
            raise

        # If not successful response or analysis error from WebID, log the error and return an empty result
        if not webid_response_is_success(r):
            # Server returned analysis failure
            logging.error("WebID analysis failed for file %s: status %s", ff, r.status_code)
            data = {}
        else:
            data = r.json()
        # Parse isotopes list (may be empty)
        isotopes = data.get('isotopes', []) or []
        # Build ID list or default empty identification
        if isotopes:
            ids = [(item.get('name', ''), str(item.get('confidence', 0))) for item in isotopes]
        else:
            ids = [('', '0')]

        id_report = etree.Element('IdentificationResults')
        for id_iso, id_conf in ids:
            id_result = etree.SubElement(id_report, 'Identification')
            id_name = etree.SubElement(id_result, 'IDName')
            id_name.text = id_iso
            id_confidence = etree.SubElement(id_result, 'IDConfidence')
            id_confidence.text = id_conf
        indent(id_report)

        etree.ElementTree(id_report).write(
            os.path.join(outputdir, ff.replace(".n42", ".res")),
            encoding='utf-8', xml_declaration=True, method='xml'
        )

def get_DRFList_from_webid(url='https://full-spectrum.sandia.gov/'):
    """
    Fetch the list of available detector response functions (DRFs) from the WebID API.

    :param url: Base URL of the WebID API.
    :returns: List of DRF identifiers, or None if the request fails.
    """
    try:
        r = requests.post(f'{url.strip().strip('/')}/api/v1/info')
    except Exception as e:
        print(e)
        return None

    if r:
        options = r.json().get('Options', [])
        if options:
            return options[0].get('possibleValues')
    return None
