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
import shlex
import shutil
import subprocess
import sys
import traceback
import logging

from PySide6.QtCore import QCoreApplication

from src.contexts import SimContext
from src.table_def import ReplayTypes
from src.rase_settings import RaseSettings, APPLICATION_PATH
from src.rase_functions import get_replay_input_dir, get_replay_output_dir, files_endswith_exists, \
    get_sample_dir, get_ids_from_webid, get_results_dir, files_exist

# translation_tag = 'rep_g'

# On Windows platforms, pass this startupinfo to avoid showing the console when running a process via popen
popen_startupinfo = None
if sys.platform.startswith("win"):
    popen_startupinfo = subprocess.STARTUPINFO()
    popen_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    popen_startupinfo.wShowWindow = subprocess.SW_HIDE


class ReplayGeneration:
    def __init__(self, sim_context_list: list[SimContext], settings=None):
        self.sim_context_list = sim_context_list
        self.settings = settings
        self.n = len(self.sim_context_list)
        self.progress = self._gui_progress_bar()
        if settings is None:
            self.settings = RaseSettings()

    def runReplay(self):
        """
        Execute replay process
        """
        sampleRootDir = self.settings.getSampleDirectory()
        for i, sim_context in enumerate(self.sim_context_list):
            detector = sim_context.detector
            scenario = sim_context.scenario
            replay = sim_context.replay

            if replay and replay.is_defined():
                self._gui_set_value(i)
                self._gui_set_label(QCoreApplication.translate('rep_g', 'Replay in progress for {}...').format(detector.name))
                if replay.type == ReplayTypes.standalone:
                    if replay.is_cmd_line:
                        if replay.exe_path.endswith('.py'):
                            replayExe = [sys.executable, replay.exe_path]
                        else:
                            replayExe = [replay.exe_path]
                        sampleDir = get_replay_input_dir(sampleRootDir, detector, replay, scenario.id).replace('\\', '/')
                        if not os.path.exists(sampleDir):
                            # TODO: eventually we will generate samples directly from here.
                            pass
                        if not files_endswith_exists(sampleDir, ('.n42', replay.input_filename_suffix)):
                            continue
                        resultsDir = None
                        try:
                            resultsDir = get_replay_output_dir(sampleRootDir, detector, replay, scenario.id).replace('\\', '/')
                            settingsList = shlex.split(replay.settings)
                            for index in [idx for idx, s in enumerate(settingsList) if 'INPUTDIR' in s]:
                                settingsList[index] = settingsList[index].replace('INPUTDIR', sampleDir)
                            for index in [idx for idx, s in enumerate(settingsList) if 'OUTPUTDIR' in s]:
                                settingsList[index] = settingsList[index].replace('OUTPUTDIR', resultsDir)
                            if 'CMDTrustID' in replayExe[0]:
                                for idx in range(2):
                                    settingsList[idx] = settingsList[idx].replace('/', "\\")
                            if os.path.exists(resultsDir):
                                shutil.rmtree(resultsDir)
                            os.makedirs(resultsDir, exist_ok=True)

                            # The stdout and stderr of the replay tool (if any) are sent to a log file
                            stdout_file = open(os.path.join(get_sample_dir(sampleRootDir, detector, scenario.id),
                                                f"replay_tool_output_{replay.id}.log"), mode='w')

                            replayargs= replayExe + settingsList

                            # On Windows, running this from the binary produced by Pyinstaller
                            # with the ``--noconsole`` option requires redirecting everything
                            # (stdin, stdout, stderr) to avoid an OSError exception
                            # "[Error 6] the handle is invalid."
                            # See: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
                            # don't pass startup_info because it freezes execution of some replay tools
                            if 'Target' in replayExe[0]:
                                # Target replay tools look for the dimensions of an
                                # executable window during operation, so we must create one
                                p = subprocess.Popen(replayargs, stdin=subprocess.DEVNULL,
                                                     stderr=stdout_file, stdout=stdout_file,
                                                     shell=sys.platform == 'win32',
                                                     creationflags=subprocess.DETACHED_PROCESS,
                                                     cwd=APPLICATION_PATH)
                            else:
                                p = subprocess.Popen(replayargs, stdin=subprocess.DEVNULL,
                                                     stderr=stdout_file, stdout=stdout_file,
                                                     shell=sys.platform == 'win32',
                                                     cwd=APPLICATION_PATH)
                            stdout_file.flush()
                            stdout_file.close()
                            # TODO: consolidate results of errors in one message box
                            stderr, stdout = p.communicate()

                            if 'CMDTrustID' in replayExe[0]:
                                resdir = os.path.join(resultsDir, 'RES')
                                for f in os.listdir(resdir):
                                    shutil.move(os.path.join(resdir, f), os.path.join(resultsDir, f))
                                os.rmdir(os.path.join(resultsDir, 'N42'))
                                os.rmdir(resdir)
                        except Exception as e:
                            self._gui_set_value(self.n + 1)
                            traceback.print_exc()
                            logging.exception(QCoreApplication.translate('rep_g', 'Handled Exception'), exc_info=True)
                            self._gui_QCritical(QCoreApplication.translate('rep_g', 'Replay failed'),
                                    QCoreApplication.translate('rep_g', 'Could not execute '
                                    'replay for instrument {}, replay {}, and scenario {}<br><br>').format(detector.name, replay.name, scenario.id) + str(e))
                            if resultsDir is not None:
                                shutil.rmtree(resultsDir)
                            return
                        self._gui_set_value(i)
                    else:
                        sampleDir = get_replay_input_dir(sampleRootDir, detector, replay, scenario.id)
                        if not os.path.exists(sampleDir):
                            # TODO: eventually we will generate samples directly from here.
                            pass
                        if not files_endswith_exists(sampleDir, ('.n42',)):
                            continue
                        resultsDir = get_replay_output_dir(sampleRootDir, detector, replay, scenario.id)
                        if os.path.exists(resultsDir):
                            shutil.rmtree(resultsDir)
                        os.makedirs(resultsDir, exist_ok=True)
                        # FIXME: this works only on Windows
                        os.startfile(replay.exe_path)
                        self._gui_QInformation(QCoreApplication.translate('rep_g', 'Manual Replay Tool'),
                               QCoreApplication.translate('rep_g', 'Replay tool has been '
                                 'opened in a separate window and must be run manually.<br>'
                                 'Press OK when done.<br><br>Use the following settings:<br>'
                                'Input folder:<br> {}<br><br>Output folder:<br> {}<br>').format(sampleDir, resultsDir))
                        self._gui_set_value(i)
                    self._gui_update_colors()
                elif replay.type == ReplayTypes.gadras_web:
                    sampleDir = get_replay_input_dir(sampleRootDir, detector, replay, scenario.id)
                    if not files_endswith_exists(sampleDir, ('.n42', replay.input_filename_suffix)):
                        continue
                    resultsDir = None
                    try:
                        resultsDir = get_replay_output_dir(sampleRootDir, detector, replay, scenario.id)
                        if os.path.exists(resultsDir):
                            shutil.rmtree(resultsDir)
                        os.makedirs(resultsDir, exist_ok=True)
                        get_ids_from_webid(sampleDir, resultsDir, replay.drf_name,
                                           replay.web_address, synthesize_bkg=(
                                            not detector.includeSecondarySpectrum))

                    except Exception as e:
                        self._gui_set_value(self.n + 1)
                        traceback.print_exc()
                        logging.exception(QCoreApplication.translate('rep_g', 'Handled Exception'), exc_info=True)
                        self._gui_QCritical(QCoreApplication.translate('rep_g', 'Replay failed'),
                                QCoreApplication.translate('rep_g', 'Could not execute replay {}'
                              'for instrument {} and scenario {}<br><br>').format(replay.name, detector.name, scenario.id) + str(e))
                        if resultsDir is not None:
                            shutil.rmtree(resultsDir)
                        return
        self._gui_set_value(self.n+1)

        translator = TranslationGeneration(self.sim_context_list, self.settings)
        translate_status = translator.runTranslator()
        return translate_status

    def _gui_progress_bar(self):
        return None

    def _gui_set_value(self, value):
        pass

    def _gui_set_label(self, label):
        pass

    def _gui_QCritical(self, err_name='', err_message=''):
        pass

    def _gui_QInformation(self, info_name='', info_message=''):
        pass

    def _gui_update_colors(self):
        pass


class TranslationGeneration:
    def __init__(self, sim_context_list: list[SimContext], settings=None):
        self.sim_context_list = sim_context_list
        self.settings = settings
        if settings is None:
            self.settings = RaseSettings()
        self.progress = self._gui_progress_bar()
        self.n = len(self.sim_context_list)

        # On Windows platforms, pass this startupinfo to avoid showing the console when running a process via popen
        self.popen_startupinfo = None
        if sys.platform.startswith("win"):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE

    def runTranslator(self):
        """
        Launches Translate Results
        """
        sampleRootDir = self.settings.getSampleDirectory()
        for i, sim_context in enumerate(self.sim_context_list):
            detector = sim_context.detector
            scenario = sim_context.scenario
            replay = sim_context.replay
            self._gui_set_value(i)
            if replay and replay.translator_exe_path and replay.translator_is_cmd_line:
                self._gui_set_label(QCoreApplication.translate('rep_g',
                                                               'Translation in progress for {} | {} | {}...')
                                    .format(detector.name, replay.name, scenario.id))
                self._gui_set_value(i)

                # input dir to this module
                input_dir = get_replay_output_dir(sampleRootDir, detector, replay, scenario.id)
                output_dir = get_results_dir(sampleRootDir, detector, replay, scenario.id)

                if not files_exist(input_dir):
                    continue

                command = [replay.translator_exe_path]
                if replay.translator_exe_path.endswith('.py'):
                    command = [sys.executable, replay.translator_exe_path]

                # FIXME: the following assumes that INPUTDIR and OUTPUTDIR are present only one time each in the settings
                settingsList = shlex.split(replay.translator_settings)
                if "INPUTDIR" in settingsList:
                    settingsList[settingsList.index("INPUTDIR")] = input_dir
                if "OUTPUTDIR" in settingsList:
                    settingsList[settingsList.index("OUTPUTDIR")] = output_dir

                command = command + settingsList

                try:
                    # On Windows, running this from the binary produced by Pyinstaller
                    # with the ``--noconsole`` option requires redirecting everything
                    # (stdin, stdout, stderr) to avoid an OSError exception
                    # "[Error 6] the handle is invalid."
                    # See: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
                    p = subprocess.run(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, encoding='utf-8', check=True,
                                       startupinfo=popen_startupinfo, cwd=APPLICATION_PATH)
                except subprocess.CalledProcessError as e:
                    self._gui_set_value(self.n + 1)
                    log_fname = os.path.join(get_sample_dir(sampleRootDir, detector, scenario.id),
                                             f'results_translator_output_{replay.id}.log')
                    log = open(log_fname, 'w')
                    log.write(QCoreApplication.translate('rep_g', '### Command: ') + os.linesep)
                    log.write(' '.join(e.cmd) + os.linesep)
                    log.write(QCoreApplication.translate('rep_g', '### Output: ') + os.linesep)
                    log.write(e.output)
                    log.close()
                    self._gui_QCritical(QCoreApplication.translate('rep_g', 'Error!'),
                            QCoreApplication.translate('rep_g', 'Results translation exited '
                                'with error code {} when running translator.<br><br>Output '
                                'log at: <br>{}').format(str(e.returncode), log_fname))
                    shutil.rmtree(output_dir, ignore_errors=True)
                    return False
                except Exception as e:
                    traceback.print_exc()
                    logging.exception(QCoreApplication.translate('rep_g', 'Handled Exception'), exc_info=True)
                    self._gui_set_value(self.n + 1)
                    self._gui_QCritical(QCoreApplication.translate('rep_g', 'Error!'),
                            QCoreApplication.translate('rep_g', 'Results translation failed '
                                    'for instrument {}, replay {}, and scenario {}<br><br>')
                                        .format(detector.name, replay.name, scenario.id) + str(e))
                    shutil.rmtree(output_dir, ignore_errors=True)
                    return False
        self._gui_set_value(self.n + 1)
        return True

    def _gui_progress_bar(self):
        return None

    def _gui_QCritical(self, err_name='', err_message=''):
        pass

    def _gui_set_value(self, value):
        pass

    def _gui_set_label(self, label):
        pass

