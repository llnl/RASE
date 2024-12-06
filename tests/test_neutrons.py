
import sys
from time import sleep

import pytest

from src.detector_dialog import DetectorDialog, DetectorModel
from src.base_spectra_dialog import BaseSpectraDialog
import src.scenario_dialog as scenario_dialog
from src.rase_functions import *
from .fixtures import temp_data_dir, db_and_output_folder, HelpObjectCreation, main_window, filled_db
from src.spectra_generation import SampleSpectraGeneration
from src.contexts import SimContext
from itertools import product
import pytest
import src.neutrons as neutrons


@pytest.fixture(scope="class")
def neutron_objects():
    #create neutron source
    hoc = HelpObjectCreation()
    hoc.create_default_workflow()
    dets, scens = hoc.get_default_workflow_objects()
    det = dets[0]
    scen = scens[0]

    #########
    scen.scen_materials[0].neutron_dose=1.9876

    det.base_spectra[0].neutrons = 0 # base spectra shouldn't need this field to have a nonzero value.
    det.base_spectra[0].neutron_sensitivity = 1
    #########

    return det, scen


example_neutron_base_spectrum = '''
<?xml version='1.0' encoding='UTF-8'?>
<RadInstrumentData>
  <RadMeasurement id="Foreground">
    <MeasurementClassCode>Foreground</MeasurementClassCode>
    <RealTimeDuration>PT2M0.000053S</RealTimeDuration>
    <Spectrum>
      <LiveTimeDuration Unit="sec">PT1M59.978549S</LiveTimeDuration>
      <ChannelData>0.0000 0.0000 0.0000 0.0000 0.0000 18.0000 19.0000 22.0000 20.0000 21.0000 22.0000 21.0000 31.0000 32.0000 28.0000 25.0000 16.0000 25.0000 33.0000 36.0000 44.0000 35.0000 42.0000 45.0000 51.0000 70.0000 67.0000 72.0000 75.0000 67.0000 81.0000 78.0000 83.0000 88.0000 86.0000 78.0000 87.0000 76.0000 87.0000 75.0000 64.0000 83.0000 82.0000 67.0000 76.0000 84.0000 87.0000 66.0000 71.0000 70.0000 68.0000 66.0000 61.0000 59.0000 64.0000 58.0000 62.0000 63.0000 53.0000 66.0000 49.0000 46.0000 43.0000 53.0000 57.0000 45.0000 51.0000 62.0000 51.0000 48.0000 32.0000 37.0000 58.0000 51.0000 48.0000 57.0000 59.0000 53.0000 43.0000 50.0000 44.0000 50.0000 43.0000 38.0000 30.0000 34.0000 40.0000 44.0000 45.0000 30.0000 28.0000 18.0000 31.0000 27.0000 26.0000 19.0000 22.0000 20.0000 30.0000 38.0000 32.0000 23.0000 26.0000 27.0000 21.0000 26.0000 15.0000 14.0000 9.0000 28.0000 13.0000 25.0000 11.0000 22.0000 7.0000 13.0000 15.0000 14.0000 14.0000 19.0000 19.0000 17.0000 5.0000 12.0000 12.0000 13.0000 14.0000 13.0000 14.0000 18.0000 9.0000 10.0000 7.0000 12.0000 14.0000 9.0000 15.0000 18.0000 14.0000 8.0000 8.0000 13.0000 7.0000 11.0000 9.0000 6.0000 9.0000 9.0000 11.0000 6.0000 11.0000 8.0000 10.0000 7.0000 10.0000 8.0000 6.0000 9.0000 6.0000 8.0000 13.0000 7.0000 5.0000 11.0000 11.0000 14.0000 11.0000 11.0000 13.0000 17.0000 15.0000 25.0000 20.0000 20.0000 26.0000 21.0000 17.0000 28.0000 11.0000 16.0000 11.0000 16.0000 13.0000 15.0000 13.0000 11.0000 11.0000 6.0000 10.0000 7.0000 9.0000 2.0000 8.0000 9.0000 6.0000 9.0000 8.0000 9.0000 4.0000 7.0000 7.0000 3.0000 8.0000 2.0000 8.0000 7.0000 7.0000 8.0000 8.0000 4.0000 5.0000 5.0000 10.0000 5.0000 7.0000 6.0000 6.0000 9.0000 7.0000 7.0000 6.0000 8.0000 5.0000 3.0000 6.0000 9.0000 9.0000 10.0000 2.0000 5.0000 3.0000 5.0000 5.0000 3.0000 6.0000 4.0000 3.0000 2.0000 5.0000 3.0000 3.0000 2.0000 2.0000 3.0000 4.0000 3.0000 12.0000 5.0000 4.0000 7.0000 0.0000 8.0000 4.0000 6.0000 4.0000 7.0000 3.0000 5.0000 4.0000 6.0000 4.0000 8.0000 2.0000 5.0000 4.0000 6.0000 7.0000 5.0000 7.0000 6.0000 7.0000 5.0000 2.0000 4.0000 4.0000 6.0000 8.0000 6.0000 13.0000 5.0000 4.0000 2.0000 4.0000 2.0000 9.0000 5.0000 9.0000 4.0000 3.0000 7.0000 4.0000 3.0000 7.0000 3.0000 5.0000 4.0000 13.0000 1.0000 2.0000 2.0000 2.0000 5.0000 8.0000 9.0000 5.0000 7.0000 3.0000 4.0000 5.0000 10.0000 8.0000 5.0000 3.0000 5.0000 4.0000 5.0000 6.0000 5.0000 5.0000 1.0000 5.0000 3.0000 6.0000 3.0000 5.0000 4.0000 4.0000 4.0000 5.0000 1.0000 3.0000 5.0000 3.0000 4.0000 6.0000 4.0000 3.0000 2.0000 6.0000 6.0000 7.0000 2.0000 7.0000 4.0000 7.0000 3.0000 4.0000 3.0000 2.0000 5.0000 2.0000 3.0000 5.0000 3.0000 2.0000 3.0000 2.0000 2.0000 4.0000 2.0000 7.0000 5.0000 5.0000 8.0000 2.0000 3.0000 2.0000 1.0000 6.0000 4.0000 2.0000 1.0000 5.0000 0.0000 1.0000 2.0000 2.0000 1.0000 2.0000 3.0000 3.0000 9.0000 2.0000 7.0000 5.0000 4.0000 3.0000 7.0000 0.0000 7.0000 7.0000 6.0000 3.0000 4.0000 6.0000 3.0000 6.0000 4.0000 7.0000 5.0000 8.0000 4.0000 6.0000 5.0000 4.0000 0.0000 8.0000 5.0000 4.0000 5.0000 1.0000 4.0000 1.0000 2.0000 2.0000 6.0000 1.0000 2.0000 5.0000 5.0000 3.0000 5.0000 4.0000 1.0000 2.0000 1.0000 5.0000 5.0000 2.0000 2.0000 3.0000 3.0000 3.0000 5.0000 3.0000 5.0000 5.0000 8.0000 7.0000 1.0000 4.0000 2.0000 2.0000 2.0000 7.0000 6.0000 2.0000 8.0000 5.0000 3.0000 5.0000 6.0000 4.0000 7.0000 3.0000 4.0000 4.0000 1.0000 3.0000 3.0000 1.0000 1.0000 2.0000 3.0000 2.0000 0.0000 2.0000 0.0000 0.0000 0.0000 0.0000 0.0000 2.0000 1.0000 0.0000 1.0000 0.0000 1.0000 3.0000 1.0000 0.0000 4.0000 3.0000 1.0000 1.0000 1.0000 2.0000 2.0000 0.0000 0.0000 1.0000 2.0000 2.0000 2.0000 0.0000 1.0000 1.0000 2.0000 2.0000 0.0000 0.0000 0.0000 1.0000 1.0000 1.0000 1.0000 1.0000 1.0000 2.0000 0.0000 1.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 2.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 1.0000 0.0000 1.0000 0.0000 0.0000 0.0000 1.0000 1.0000 0.0000 0.0000 1.0000 2.0000 0.0000 0.0000 1.0000 0.0000 0.0000 2.0000 0.0000 0.0000 0.0000 1.0000 0.0000 1.0000 2.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 2.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 1.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000</ChannelData>
      <RASE_Sensitivity>61.352633961259194</RASE_Sensitivity> <FLUX_Sensitivity>61.352633961259194</FLUX_Sensitivity>
    </Spectrum>
    <GrossCounts id="neutrons">
      <neutron_Sensitivity>0.1</neutron_Sensitivity>
    </GrossCounts>
  </RadMeasurement>
  <EnergyCalibration>
    <CoefficientValues>-6.881231 2.920997 0.000105861</CoefficientValues>
  </EnergyCalibration>
  <RadMeasurement id="CalMeasurementGamma-SG_60017-01341">
    <MeasurementClassCode>Calibration</MeasurementClassCode>
    <StartDateTime>2020-10-07T17:55:52.431+00:00</StartDateTime>
    <RealTimeDuration>PT35.259016117S</RealTimeDuration>
    <Spectrum id="GammaCal" radDetectorInformationReference="DetectorInfoGamma" energyCalibrationReference="ECalGamma-SG_60017-01341" FWHMCalibrationReference="RCalGamma-SG_60017-01341">
      <Remark>Title: Gamma Cal</Remark>
      <LiveTimeDuration>PT35.054216315S</LiveTimeDuration>
      <ChannelData compressionCode="CountedZeroes">0 5 900 672 632 720 618 499 623 1104 2459 5427 7192 5661 3171 1919 934 466 301 274 261 270 321 373 474 651 763 766 878 784 740 604 526 422 416 407 400 494 709 1173 1969 2661 2919 2371 1647 975 573 408 381 348 388 377 373 378 401 404 404 452 416 425 381 368 325 311 290 282 291 257 242 264 268 270 245 271 290 288 230 285 281 315 342 391 424 453 405 461 376 354 325 246 242 187 209 206 212 191 177 168 176 241 196 210 181 202 187 181 190 183 170 200 231 278 341 437 476 559 613 678 685 689 664 636 585 504 370 323 306 259 175 150 142 110 114 125 125 104 91 99 89 100 93 119 82 92 89 80 101 97 100 87 95 88 99 76 90 99 85 76 75 70 70 67 55 63 72 70 72 66 67 63 48 69 75 81 78 73 55 70 63 72 75 58 59 51 45 64 56 50 53 48 57 59 65 58 60 57 53 63 63 48 43 44 46 50 45 45 37 47 50 48 34 42 46 54 46 32 42 52 40 54 35 54 35 57 36 42 55 60 36 46 54 49 58 53 47 66 47 43 50 55 51 53 44 53 49 43 49 39 40 49 56 51 57 55 57 62 59 51 65 67 64 86 77 71 84 75 62 67 75 56 72 65 42 58 42 53 38 38 29 30 41 42 26 32 32 37 38 41 45 35 54 36 37 38 32 53 46 45 29 31 45 36 35 31 28 24 42 23 28 22 27 30 27 30 35 44 47 43 50 52 54 68 55 58 42 41 38 52 42 35 44 39 41 35 31 38 40 36 24 24 23 19 28 26 15 22 21 18 27 14 29 23 34 33 28 34 29 38 33 31 51 48 49 44 41 50 67 64 61 54 68 57 51 75 57 50 51 57 37 44 43 29 37 24 28 34 28 26 19 24 24 19 11 19 9 15 15 8 6 10 10 11 10 4 11 11 9 8 9 10 9 7 14 13 3 9 11 8 10 13 9 7 10 7 6 11 5 3 7 5 4 9 5 11 4 4 4 5 10 1 5 4 4 2 11 4 3 3 5 2 6 4 4 4 5 8 7 12 8 21 14 21 17 12 16 19 28 25 27 23 13 26 27 37 25 28 21 38 22 31 17 31 19 13 18 13 14 11 7 13 6 5 4 4 2 2 5 3 3 2 2 3 1 3 0 1 3 5 3 1 1 0 1 2 3 3 2 1 2 1 1 3 4 5 1 0 1 5 1 1 2 2 0 1 1 3 1 0 1 1 1 0 5 1 1 0 10 1 0 4 1 0 3 1 0 1 1 1 1 0 2 1 0 1 1 0 3 1 0 2 1 0 4 1 1 0 70 1 1 1 1 0 103 1 0 5 1 0 67 1 0 14 1 0 6 1 0 3 1 0 10 1 0 1 1 0 8 1 0 136 </ChannelData>
    </Spectrum>
  </RadMeasurement>
  <RadMeasurement id="BackgroundMeasure7d4180000002" radMeasurementGroupReferences="BackgroundMeasurements-1">
    <MeasurementClassCode>Background</MeasurementClassCode>
    <StartDateTime>2023-01-03T14:29:52.566-06:00</StartDateTime>
    <RealTimeDuration>PT300.200323353S</RealTimeDuration>
    <Spectrum id="GammaBackgroundMeasure7d4180000002" radDetectorInformationReference="DetectorInfoGamma" energyCalibrationReference="ECalGamma-SG_60017-01341" FWHMCalibrationReference="RCalGamma-SG_60017-01341">
      <Remark>Title: Gamma BackgroundMeasure7d4180000002</Remark>
      <LiveTimeDuration>PT300.154584577S</LiveTimeDuration>
      <ChannelData compressionCode="CountedZeroes">0 5 35 32 39 33 43 54 50 51 49 37 52 48 48 52 62 55 60 74 81 93 111 91 121 156 120 133 146 148 154 154 145 180 168 179 168 166 161 141 169 152 155 160 173 162 159 158 152 141 138 142 130 120 140 134 129 124 103 126 96 107 110 97 106 117 92 110 111 99 82 106 98 86 78 74 78 85 84 74 72 66 71 77 56 64 62 55 57 51 54 65 64 53 58 47 50 45 47 48 52 51 47 49 39 38 33 41 47 35 32 30 40 43 42 35 27 32 33 36 34 26 38 36 21 22 29 28 25 21 15 20 24 33 18 13 20 15 17 16 14 13 12 22 12 16 16 20 15 18 12 16 14 19 19 18 19 20 15 18 21 25 22 28 32 31 32 45 32 35 44 50 51 55 57 58 48 44 38 39 27 26 20 15 20 8 10 12 15 14 17 12 15 10 9 5 12 12 8 14 8 15 10 11 18 11 10 10 9 9 7 5 5 11 6 6 10 8 10 4 5 8 12 6 6 6 4 5 4 5 7 3 5 6 2 10 6 4 4 3 2 4 8 5 6 6 6 10 3 8 7 7 9 8 10 7 6 3 3 9 6 7 4 6 6 9 4 4 7 6 8 8 6 8 3 5 10 8 6 4 7 5 3 7 5 4 8 7 8 4 5 5 6 11 7 4 6 2 1 5 7 8 8 2 6 4 4 5 4 2 5 8 5 9 3 5 6 10 7 7 3 3 5 6 6 3 8 5 6 9 6 4 7 5 6 7 6 11 7 5 4 2 7 4 5 3 7 5 6 2 4 3 7 4 3 5 2 7 5 4 3 4 5 3 2 4 4 4 3 1 5 4 7 6 2 6 6 0 1 3 1 1 1 7 1 7 3 9 2 5 3 3 3 2 5 5 2 2 2 4 4 5 1 3 2 2 1 3 4 1 5 6 2 2 4 0 1 6 8 8 4 3 7 4 5 4 8 15 6 9 12 13 7 8 5 7 9 1 4 4 4 2 5 0 1 3 1 3 3 4 0 1 1 4 2 2 2 0 1 1 2 0 1 2 0 1 1 1 0 2 2 4 2 3 0 1 3 3 5 2 0 1 1 3 2 1 2 4 6 1 1 2 5 3 2 3 0 1 7 2 5 6 3 5 4 2 2 2 6 3 2 5 4 3 1 1 1 4 2 3 2 2 1 2 1 1 0 1 1 1 2 1 0 1 1 4 0 1 1 0 1 1 0 1 2 0 3 1 1 1 1 0 2 1 2 3 1 0 3 1 1 0 18 1 0 1 1 1 0 1 2 0 1 1 1 2 1 1 0 2 2 1 1 1 0 2 3 0 2 1 0 1 1 0 1 2 2 0 1 1 0 1 1 0 2 1 0 1 3 0 1 1 0 2 2 1 0 8 1 0 3 1 0 4 1 0 13 1 0 2 1 2 1 0 17 1 0 1 1 0 2 1 1 1 0 2 1 1 1 0 4 1 0 15 1 0 18 1 0 14 1 0 11 2 1 1 1 0 12 1 0 4 2 0 3 1 1 1 0 13 1 0 4 1 0 11 1 0 16 1 0 10 1 0 14 1 0 4 1 0 1 1 0 7 1 0 7 1 0 1 2 0 1 2 0 4 1 1 1 0 8 2 0 2 1 0 18 1 0 8 1 0 4 1 0 5 1 0 46 1 0 4 1 0 39 </ChannelData>
    </Spectrum>
     
    <Degraded>false</Degraded>
    <ScaleFactor>1</ScaleFactor>
  </RadMeasurement>

</RadInstrumentData>'''


class Test_neutrons_basic:
    def test_neutron_counts(self, qtbot, neutron_objects):
        det, scen = neutron_objects
        counts, expected = neutrons.neutron_foreground(scen,det)
        assert(counts>0)

    def test_spec_gen(self, qtbot, neutron_objects):
        det, scen = neutron_objects
        detector_scenarios = [SimContext(detector=d, replay=None, scenario=s) for d, s in product([det], [scen])]
        spec_generation = SampleSpectraGeneration(detector_scenarios)
        spec_generation.work()

class Test_neutrons_mvc:
    def test_scen_column_hidden_if_no_neutrons(self, qtbot,main_window, filled_db):
        d = scenario_dialog.ScenarioDialog(main_window)
        assert not d.get_neutrons_visible()

    def test_neutron_display_blank(self, qtbot, filled_db,main_window):
        dets, scens = filled_db.get_default_workflow_objects()
        d = DetectorDialog(main_window,dets[0].name)
        assert(d.neutrons_label.text() == '')

    def test_add_det_neutrons(self, qtbot, filled_db,main_window,temp_data_dir):
        dets, scens = filled_db.get_default_workflow_objects()

        # Make a base spectrum file in the temp data directory
        basefolder = Path(temp_data_dir) / 'base_spectra'
        basefolder.mkdir(exist_ok=True)
        with open(basefolder/'VTEST_MExample_Co60.n42',mode='w') as file:
            file.writelines(example_neutron_base_spectrum)

        with open(basefolder/'VTEST_MExample_Bgnd.n42',mode='w') as file:
            file.writelines(example_neutron_base_spectrum)


        d = DetectorDialog(main_window,dets[0].name)
        b = BaseSpectraDialog()
        qtbot.addWidget(b)
        b.on_btnBrowse_clicked(False,
                               str(basefolder)
                               )
        b.accept()

        d.on_btnAddBaseSpectra_clicked(False, b)
        d.accept()
        dets, scens = filled_db.get_default_workflow_objects()

    def test_add_scen_neutrons(self,qtbot,filled_db, main_window):
        dets, scens = filled_db.get_default_workflow_objects()

        id = scens[0].id
        d = scenario_dialog.ScenarioDialog(main_window,id)
        assert d.get_neutrons_visible()
        model = d.model

        edit_index = model.modelSource.index(0,scenario_dialog.INTENSITY_NEUTRON)
        model.modelSource.setData(edit_index,'1.23')
        edit_index = model.modelSource.index(0, scenario_dialog.MATERIAL)
        model.modelSource.setData(edit_index, 'Co60')
        d.accept()
        dets, scens = filled_db.get_default_workflow_objects()
        assert scens[0].scen_materials[0].neutron_dose == 1.23

    def test_spec_gen(self, qtbot, filled_db):
        dets, scens = filled_db.get_default_workflow_objects()
        detector_scenarios = [SimContext(detector=d, replay=None, scenario=s) for d, s in product([dets[0]], [scens[0]])]
        spec_generation = SampleSpectraGeneration(detector_scenarios)
        dets[0].replays[0].n42_template_path = str(Path(__file__).parent/'../n42Templates/example_neutrons_template.n42') #assign template so templating is tested
        spec_generation.work()

    ##Optional TODO: test that templated file is actually filled. Need to figure out how to get that file path.

    def test_neutron_counts(self, qtbot, filled_db):
        dets, scens = filled_db.get_default_workflow_objects()
        counts, expected = neutrons.neutron_foreground(scens[0], dets[0])
        print(counts, expected)
        assert counts > 0

    def test_neutron_display(self, qtbot, filled_db,main_window):
        dets, scens = filled_db.get_default_workflow_objects()
        d = DetectorDialog(main_window, dets[0].name)
        assert d.neutrons_label.text() == 'BG neutron detection rate: 0.100 nps'

