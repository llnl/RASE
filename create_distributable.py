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

import os
import glob
import sys
from shutil import copytree, rmtree, copy
import platform

dirname = os.path.abspath(os.path.dirname(__file__))
templatepath_name = "n42Templates"
basespectra_name = "baseSpectra"
buildpath = os.path.join(dirname, "build")
distpath = os.path.join(dirname, "dist")

if not os.path.exists(distpath):
    os.makedirs(distpath)

# Ensure latest ui
r = os.system(sys.executable + " build-ui.py")
if r: exit(r)

# Ensure documentation is compiled
r = os.system(f"sphinx-build -M html \"{os.path.join(dirname, 'doc')}\" \"{os.path.join(dirname, 'doc', '_build')}\"")
if r: exit(r)

# Generate the binary QM format used by QTranslator objects for all translations files
ts_files = glob.glob('translations/*.ts')
for ts_file in ts_files:
    r = os.system(f"lrelease {ts_file}")
    if r: exit(r)

# Main RASE app
options = "--onedir --windowed" if platform.system() == "Darwin" else ""
r = os.system(sys.executable + " -m PyInstaller -y " + options +
          " --distpath \"" + distpath +
          "\" --workpath \"" + buildpath +
          "\" rase.spec")
if r: exit(r)

# Templates and base spectra
for source_name in (templatepath_name, basespectra_name):
    destination_path = os.path.join(distpath, source_name)
    rmtree(destination_path, ignore_errors=True)
    copytree(os.path.join(dirname, source_name), destination_path)

# tools
tools_path = os.path.join(distpath, "ReplayTools")
rmtree(tools_path, ignore_errors=True)
os.makedirs(tools_path)
wrappers = ['BNC_SAM9X0-ReplayTool-Wrapper.cmd', 'BTI-FSX5600-ReplayTool-Wrapper.cmd',
            'DetectiveX_replaytool_wrapper.bat', 'Dockerfile-KromekD5', 'FLIR-R440-ReplayTool-Wrapper.cmd',
            'FullSpec_replaytool_wrapper.cmd', 'KromekD5_replaytool_wrapper.sh', 'RsiRaseReplay_replaytool_wrapper.bat',
            'MeasurementParams.xml']
for wrapper in wrappers:
    copy(os.path.join(dirname, "tools", wrapper), tools_path)

# demo replay tool
r = os.system(sys.executable + " -m PyInstaller -y -F --noupx" +
          " --distpath \"" + os.path.join(distpath, 'ReplayTools') +
          "\" --workpath \"" + buildpath + "\" \"" +
          os.path.join(dirname, "tools", "demo_replay.py") + "\"")
if r: exit(r)
r = os.system(sys.executable + " -m PyInstaller -y -F --noupx" +
          " --distpath \"" + os.path.join(distpath, 'ReplayTools') +
          "\" --workpath \"" + buildpath + "\" \"" +
          os.path.join(dirname, "tools", "fixed_replay.py") + "\"")
if r: exit(r)
r = os.system(sys.executable + " -m PyInstaller -y -F --noupx" +
          " --distpath \"" + os.path.join(distpath, 'ReplayTools') +
          "\" --workpath \"" + buildpath + "\" \"" +
          os.path.join(dirname, "tools", "LAMP_ID.py") + "\"")
if r: exit(r)

# gadras api clone detector template file
demoscript_path = os.path.join(distpath, "demonstrationScripts")
rmtree(demoscript_path, ignore_errors=True)
os.makedirs(demoscript_path)
demoscripts = ['example_api_workflow.py', 'example_api_backgrounds.py', 'example_api_scurves.py',
               'gadras_clone_detector.py']
for demoscript in demoscripts:
    copy(os.path.join(dirname, 'demonstrationScripts', demoscript), demoscript_path)

example_path = os.path.join(distpath, "examples")
rmtree(example_path, ignore_errors=True)
os.makedirs(example_path)
precomputed_files = ['ANSI_scenario_import.csv', 'default_corrtable.csv', 'detimport_genericnai_wfullspec.yaml',
                     'example_api_backgrounds.yaml', 'example_api_scurves.yaml']
for precomputed in precomputed_files:
    copy(os.path.join(dirname, 'examples', precomputed), example_path)

# configuration and path default settings
config_path = os.path.join(distpath, "configs")
rmtree(config_path, ignore_errors=True)
os.makedirs(config_path)
config_files = ['base_spectra_config.yaml', 'shielding_paths_config.yaml']
for cf in config_files:
    copy(os.path.join(dirname, 'configs', cf), config_path)

# shielding library
shield_path = os.path.join(distpath, 'shielding_library')
rmtree(shield_path, ignore_errors=True)
copytree(os.path.join(dirname, 'shielding_library'), shield_path)

# Translators
r = os.system(sys.executable + " \"" + os.path.join(dirname, "translators", "create_translators_exe.py")+"\"")
if r: exit(r)

if platform.system() == "Darwin":
    import dmgbuild
    print("Creating App Bundle")
    translators_path = os.path.join(dirname, 'translators', 'dist')
    dmgbuild.build_dmg(volume_name="RASE",
                       filename=os.path.join(distpath, "rase.dmg"),
                       settings_file="dmgbuild_settings.py",
                       settings={'files': [os.path.join(distpath, 'rase.app'),
                                           translators_path,
                                           tools_path,
                                           templatepath_name,
                                           basespectra_name]},
                       )
