.. _replayToolSettings:

********************
Replay Tool Settings
********************

This section contains information on the configuration settings for the replay tools of a number of radioisotope identification instruments. These settings should be entered in the RASE "Add Replay Tool" dialog.

It is important to note that for executable and template files, the full path should be specified. This can be done using the corresponding "Browse" button within the RASE "Add Replay Tool" dialog.

Note also that some templates indicated here may be specific to a given model of an instrument, even though the replay tool may be compatible with other models as well.


Demo
====
Use this replay tool for demonstration purposes together with the ABCD-instrument Base Spectra included with the RASE code Distribution.
Note that the Demo Replay Tool generates random isotope identification results, and does not perform the analysis of  sampled spectra.
Otherwise, the spectra generation and results analysis process is performed as usual.

**Settings**

* Replay Tool:
    *  Executable: demo_replay.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: none - leave empty
    *  Suffix of input files: .n42 or empty
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


BNC SAM Instruments
===================
The ReplayPA tool works with the SAM 940, SAM 950, and SAMPack 120. RASE was successfully tested with v1.5 of the tool.

**Settings**

* Replay Tool:
    *  Executable: BNC_SAM9X0-ReplayTool-Wrapper.cmd [included with the RASE distribution. Place it in the same folder where ReplayPA.exe file is located.]
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: BNC_SAM9X0_template.n42 [change the X to a 4 or a 5 depending on if you are investigating the 940 or 950]
    *  Suffix of input files: .xml
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


BTI FlexSpec X5600
==================
RASE was successfully tested with v2.6 of the tool. Note that the BTI FlexSpec has multiple detectors inside. RASE accounts for this in the template, so scenarios for the FlexSpec should be run the same as any other.

**Settings**

* Replay Tool:
    *  Executable: BTI-FSX5600-ReplayTool-Wrapper.cmd [included with the RASE distribution. Place it in the same folder where N42Replay.exe file is located.]
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: BTI_FSX5600_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


CAEN DiscoveRAD
===============
The CAEN DiscoveRAD replay tool has been tested to work on Windows 10. When running the tool, an additional interrupting pop-up window is generated when analyzing each scenario that cannot be suppressed. As such, it is recommended that when running CAEN DiscoveRAD replay analysis, the user refrains from parallel work to limit interference in the replay tool operation.
Otherwise, regular analysis procedure applies.

**Settings**

* Replay Tool:
    *  Executable: Target.F501.ReplayTool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`-o OUTPUTDIR INPUTDIR`
* Sampled Spectra n42 Template:
    *  n42 Template File: :code:`CAEN_DiscoveRAD_XXXX_template.n42` (replace `XXXX` with `BGO` or `CLLBC` depending on instrument considered)
    *  Suffix of input files: :code:`.csv`
* Identification Results Translator:
    *  Executable: :code:`none - leave empty`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is a default entry]


FLIR IdentiFinder-2
===================
RASE code was successfully tested with 2016, 2017, and 2018 versions of the FLIR replay tool. Regular analysis procedure applies.

**Settings**

* Replay Tool:
    *  Executable: replay.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -r INPUTDIR -o OUTPUTDIR [see the replay tool manual for additional command line parameters that can be used here]
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_ID2_template_spectrum.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


FLIR R300
=========
R300 analysis uses the same replay tool as the IdentiFinder-2 with a different template file.
R300 base spectra and the RASE analysis routine were tested with the 2018 version of the replay tool.

**Settings**

* Replay Tool:
    *  Executable: replay.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -r INPUTDIR -o OUTPUTDIR [see the replay tool manual for additional command line parameters that can be used here]
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R300_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


FLIR R400
=========
R400 analysis uses the same replay tool and settings as the IdentiFinder-2.
R400 base spectra and the RASE analysis routine were tested with the 2018 version of the replay tool.

Note: Care should be taken with the selection of .n42 template, as the correct template depends on the dataset being used. If the base spectra set is taken from the INL 2018 measurement campaign, the FLIR_R400_UW-LGH_INL2018_template.n42 should be used. This template has a fixed internal calibration source spectrum that also includes the influence of background, and is necessary for the correct operation of the replay tool. Otherwise, the user may use the FLIR_R400_UW-LGH_template.n42 template, which sources the secondary spectrum from the scenario definition or one of the base spectra selected by the user (as described in the "second spectrum treatment" section of the :ref:`workflowStep1` page).


**Settings**

* Replay Tool:
    *  Executable: replay.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -r INPUTDIR -o OUTPUTDIR [see the replay tool manual for additional command line parameters that can be used here]
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R400_UW-LGH_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


FLIR R425
=========
FLIR R425 requires a different replay tool and settings than the previous FLIR instruments tested with the RASE code.
This RASE analysis routine was tested with the 2022 version of the replay tool, v425.22.1.
The R425-GN and R425-LGN instruments were tested with the 2024 version of the replay tool, v3.24.1.48. For these instruments, all the command line arguments are identical save for the templates (FLIR_R425GN_template and FLIR_R425LGN_template, respectively).


**Settings**

* Replay Tool:
    *  Executable: r425ReplayTool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR -o OUTPUTDIR -w [see the replay tool manual for additional command line parameters that can be used here]
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R425_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


FLIR R440
=========
FLIR R440 requires a different replay tool and settings than the FLIR Identifinder instruments tested with the RASE code.

**Settings**

* Replay Tool:
    *  Executable: FLIR-R440-ReplayTool-Wrapper.cmd [included with the RASE distribution. Place it in the same folder where Target.NID.ReplayTool.exe file is located.]
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R440_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]

FLIR R440 (>2022)
=================
The 2022 and beyond FLIR R440 replay tool no longer requires a wrapper. Be sure to select the template corresponding to the correct detector (LaBr vs NaI).

**Settings**

* Replay Tool:
    *  Executable: Target.R440.ReplayTool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -o OUTPUTDIR INPUTDIR
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R440_template_LaBr_2024.n42 or FLIR_R440_template_NaI_2024.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


FLIR R700
=========
The RASE analysis routine for the FLIR R700 backpack replay tool Target.F900.ReplayTool, build 2728 was tested in 2024.

**Settings**

* Replay Tool:
    *  Executable: Target.F900.ReplayTool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -o OUTPUTDIR INPUTDIR
* Sampled Spectra n42 Template:
    *  n42 Template File: FLIR_R700GN_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


GammaReality LAMP
=================
Replay of the GammaReality LAMP data requires physical access to the instrument as the replay is performed via
the API http endpoint. An executable `LAMP_ID.exe` is available in the RASE tools folder to interface RASE with the
instrument. Please follow the user manual to connect the LAMP to the computer running RASE.

**Settings**

* Replay Tool:
    *  Executable: LAMP_ID.exe
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: :code:`GammaReality_LAMP_template.json`
    *  Suffix of input files: :code:`.json`
* Identification Results Translator:
    *  Executable: :code:`none - leave empty`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is a default entry]


H3D A400/H420
=============
The H3D replay tool requires that an extra input file `MeasurementParams.xml` is provided with the analysis settings. A representative file is provided with RASE in the `tools` folder. Make sure that the command arguments of the replay tool point to the correct location of this file.

**Settings**

* Replay Tool:
    *  Executable: H3DVisualizer_2.9.5.exe
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`-i INPUTDIR -o OUTPUTDIR -m C:\RASE\tools` [update the last path with the location of the `MeasurementParams.xml` file]
* Sampled Spectra n42 Template:
    *  n42 Template File: :code:`H3D_A400_template.n42` [or H3D_H420_template.n42 for the H420]
    *  Suffix of input files: :code:`.n42`
* Identification Results Translator:
    *  Executable: :code:`none - leave empty`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is a default entry]


Kromek D5
=========
Kromek provides a replay tool for their D5 instrument, called :code:`PCSOffline`, that is packaged for Linux operating systems.
As of version 170.1.5.7, the replay tool only accepts a single file as input.  To facilitate use within RASE, which
requires processing an entire folder, a wrapper shell script :code:`KromekD5_replaytool_wrapper.sh` is provided in the :code:`tools`.

If you are not running RASE on a unix system, one way to run the replay tool on other machines is to dockerize it.
To facilitate this process, we provide the :code:`Dockerfile-KromekD5` file in the :code:`tools` folder.
Note that it assumes the :code:`PCSOffline.deb` package and the wrapper shell script are in the same directory as the :code:`Dockerfile`.
To create the image, simply run :code:`docker build -t kromek-rt -f Dockerfile-KromekD5 .`

**Settings**

* Replay Tool:
    *  Executable: path to the docker executable e.g. :code:`/usr/local/bin/docker`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`run --rm -v INPUTDIR:/data/in -v OUTPUTDIR:/data/out kromek-rt KromekD5_replaytool_wrapper.sh /data/in/ /data/out`
* Sampled Spectra n42 Template:
    *  n42 Template File: :code:`Kromek_D5_template.n42`
    *  Suffix of input files: :code:`.csv`
* Identification Results Translator:
    *  Executable: :code:`none - leave empty`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is a default entry]

Note that the Replay Tool command arguments should be entered exactly as described above.
If the replay tool fails to yield results on Windows, and if the replay tool log file says something along the lines of "no such file or directory," try opening the :code:`KromekD5_replaytool_wrapper.sh` file in Notepad++, go to edit -> EOL conversion, and change from CRLF to LF (credit to Vikas Rathore Oct 5, 2018 on Stack Overflow).


Mirion SPIR-Pack
================
RASE was tested to work with the SPIR-Pack replay tool version 1.0.4.0.

**Settings**

* Replay Tool:
    *  Executable: SPIR-Pack replay tool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -i INPUTDIR -o OUTPUTDIR -m
* Sampled Spectra n42 Template:
    *  n42 Template File: Mirion_SPIR-AceNaI_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


ORTEC DetectiveX
================
As of 2024, ORTEC has released a dedicated replay tool for the DetectiveX instrument. The tool is called DetectiveX Analysis Engine Offline Tool.  While it is a command line tool, it requires a custom wrapper code to handle the formatting of the results which are presented in a single output file when the tool is called to process all files in a given directory.  The wrapper code is available in the [`/tools/` ](tools/DetectiveX_replaytool_wrapper.bat) and should be placed in the same folder as the replay tool executable.

**Settings**

* Replay Tool:
    *  Executable: DetectiveX_replaytool_wrapper.bat
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: ORTEC_DetectiveX_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


ORTEC Other HPGe Devices
========================
RASE code was tested with the version 9.3.4 of the ORTEC command-line replay tool. Earlier versions may also work. It also can be used to analyse sampled spectra generated for ORTEC HX-2 MicroDetective, EX-1, D200, Trans-Spec, and Detective-X instruments.
Please note that on some Windows machines execution of the replay tool may fail with the following error message:
"Error reading the XML library. Error message: This implementation is not part of the Windows Platform FIPS validated cryptographic algorithms."
This error may also yield no message, leaving the user with an empty replay folder with no explanation. To resolve this issue, the user can go to the following location and disable the relevant Windows registry flag:

**Administrative Tools -> Local Security Policy -> Local Policies -> Security Options -> System Cryptography -> Use
FIPS compliant algorithms for encryption, hashing, and signing**

This option will automatically return to "enabled" upon logging out.

**Settings**

* Replay Tool:
    *  Executable: ORTEC_ID_Engine_RASE.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: ORTEC-HX_template_spectrum.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: ORTEC-CmdLineReplayTool-ResultsTranslator.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


ORTEC RadEagle and RadEaglet
============================
ORTEC RadEagle and RadEaglet instruments require a different replay tool and settings than the HPGe-based systems. These instructions are for the most current (as of 04/2023) version of the innoRIID RadEagle and RadEaglet replay tool, which have been tested to work with the 2SG (NaI) and 1LG (LaBr) versions of the instrument. This guidance is for the windows version of the replay tool, though MacOS and Linux versions also exist.

**Settings**

* Replay Tool:
    *  Executable: rp-win-intel-nai.exe
    *  Command Line checkbox: checked
    *  Command Arguments: 2048 INPUTDIR/ OUTPUTDIR/
* Sampled Spectra n42 Template:
    *  n42 Template File: ORTEC-RadEagletNaI_template.n42 [or ORTEC-RadEagletLaBr_template.n42 for the LaBr version]
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


ORTEC RadEagle and RadEaglet (Legacy 2023)
=============================================
These settings should be used with RadEaglet data collected during 2023.

**Settings**

* Replay Tool:
    *  Executable: ReplayTool_3.8.9.exe
    *  Command Line checkbox: checked
    *  Command Arguments: 2048 INPUTDIR/ OUTPUTDIR/
* Sampled Spectra n42 Template:
    *  n42 Template File: ORTEC-RadEaglet_spectrum.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


ORTEC RadEagle and RadEaglet (Legacy pre-2023)
==============================================
These settings should be used with RadEaglet data collected before 2023.

**Settings**

* Replay Tool:
    *  Executable: elia-rp.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: none - leave empty
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]
	

RapiScan Guardian 501
=====================
The RapiScan Guardian instrument has several different versions with different crystals. The arguments to run the tool are the same regardless of version except the template, which should be changed based on crystal type.

**Settings**

* Replay Tool:
    *  Executable: Target.F501.ReplayTool.exe
    *  Command Line checkbox: checked
    *  Command Arguments: -o OUTPUTDIR INPUTDIR
* Sampled Spectra n42 Template:
    *  n42 Template File: RapiScan_GuardianXXX_template.n42 [where `XXX` is either `BGO`, `NaICN`, or `LaBr`]
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is the default entry]


Smiths RadSeeker
==================
The procedure for Smiths RadSeeker CL and RadSeeker CS instruments involves a stand-alone (GUI-only) replay tool that requires a custom wrapper
to be run automatically within RASE. The wrapper is a python script provided in the :code:`tools` folder as :code:`radseeker_replay_wrapper.py`. Requires a working Python installation with the `pywinauto` package installed.

Define the instrument using the base spectra and generate sampled spectra as usual. Define the Smiths replay tool using the settings identified below.

**Settings**

* Replay Tool:
    *  Executable: radseeker_replay_wrapper.py
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR --type=NaI [or --type=LaBr]
* Sampled Spectra n42 Template:
    *  n42 Template File: Smith_RadseekerCL_template_spectrum.n42 [or Smith_RadseekerCS_template_spectrum.n42]
    *  Suffix of input files: _U.n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]

If the RadSeeker replay tool is not installed in the default directory, an additional command argument can be passed to the wrapper script to specify the path to the replay tool executable. For example, to specify the path to the replay tool executable located in the :code:`C:\RadSeeker` directory, the command arguments would be :code:`INPUTDIR OUTPUTDIR --batch_analysis_path=C:\RadSeeker`.

In the command argument :code:`--type`, use `NaI` for the RadSeeker-CS and `LaBr` for the Radseeker-CL.

Note that the script may not work correctly if the replay tool loses focus during execution. It is recommended to avoid interacting with the computer while the replay tool is running.


Symetrica Verifinder RIIDs
==========================
All Symetrica instruments use the same replay tool, with different command line arguments and templates depending on type. This section describes the potential arguments for the RIIDs, while the section below describes that for backpacks.
Please note that the Symetrica replay tool is sensitive to installation location, and issues may develop if the tool is installed somewhere other than the C: drive. Problems have also been observed when the sample spectra directory is not located on the same drive as the replay tool. To ensure smooth functionality, it is strongly recommended that any sample directory that includes Symetrica backpack sample spectra exist on the C: drive along with the replay tool.
The Symetrica detectors have an internal calibration source which is difficult to remove from base spectra. Because scaling the background will also scale this internal source, users are strongly discouraged from varying the intensity of the background spectrum for scenarios with the Symetrica instrument to avoid nonphysical results.
Finally: Symetrica units have an onboard background. This "secondary spectrum" background should be set in the RASE GUI to be 5 minutes long, in line with actual detector expectations.

**Settings**

* Replay Tool:
    *  Executable: Replay.cmd
    *  Command Line checkbox: checked
    *  Command Arguments: -r -c SYXX-N -i INPUTDIR -o OUTPUTDIR  [where `YXX` is either `N11`, `N23`, or `L23`]
* Sampled Spectra n42 Template:
    *  n42 Template File: Symetrica_SYXXY_template.n42 [where `YXXY` is either `N11`, `N23N`, or `L23N`]
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


Symetrica Verifinder Backpack
=============================
The Symetrica Verifinder backpack utilizes only static spectra for isotope identification, and requires no additional transient data for correct functionality.
The Symetrica template has been tested and verified for the SN33-N replay tool. This replay tool is compatible with base spectra sourced from backpack models SN31-N, SN32-N, and SN33-N.
The current implementation of the template makes use of a fixed background with a dose rate of 0.08 μSv/h. To ensure reliable results, when using the scenario creator tool to define scenarios for the Symetrica backpack a background spectrum of 0.08 μSv/h should be set.

**Settings**

* Replay Tool:
    *  Executable: Replay.cmd
    *  Command Line checkbox: checked
    *  Command Arguments: -r -c SN33-N -i INPUTDIR -o OUTPUTDIR
* Sampled Spectra n42 Template:
    *  n42 Template File: Symetrica_SN33N_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


ThermoFisher RadEye
===================
RASE was tested with the command line version of CMDTrustID, version 1.0.0.13.

**Settings**

* Replay Tool:
    *  Executable: CMDTrustID.exe
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]
* Sampled Spectra n42 Template:
    *  n42 Template File: ThermoFisher_RadEye_template.n42
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: none - leave empty
    *  Command Line checkbox: checked
    *  Command Arguments: INPUTDIR OUTPUTDIR [this is a default entry]


GADRAS Full Spectrum Isotope ID (web version)
=============================================
Sandia National Laboratory has released an online version of the GADRAS Isotope ID tool which is publicly available at
`https://full-spectrum.sandia.gov <https://full-spectrum.sandia.gov/>`_.
The tool is very flexible, works with standard RASE-formatted sample spectra, and may be used with any
detector so long as a suitably compatible Detector Response Function (DRF) is specified.

To use Full Spectrum ID as the identification algorithm in RASE, simply select the "Full Spectrum Web ID" option in the :code:`Edit
Replay Software` menu. The web address to access the WebID server is already pre-populated. The user must select the
appropriate DRF from the drop-down list. The updated list can be retrieved by clicking on the corresponding button.
Once configured, RASE will take care of sending spectra to the server and parsing the results automatically.

Spectra supplied to Full Spectrum should contain a secondary background for optimal results.  Please configure
the detector accordingly using the :code:`Edit Detector` dialog.


GADRAS Full Spectrum Isotope ID (standalone version)
====================================================
A standalone version of the GADRAS Full Spectrum Isosope ID is also available as an executable.
This can be run in two modes: (1) as a web server, and (2) as a standard command line replay tool. When run in web
server mode, the tool works equivalent as the one on the public website (described above), but running on the
localhost at `http://127.0.0.1:8002 <http://127.0.0.1:8002>`_.

If the user is using the command line capability, use the settings that follow. The command line tool is made to accept files
one at a time, so a wrapper shell script has been written to accommodate RASE directory structure. The
:code:`FullSpec_replaytool_wrapper.sh` can be found in the :code:`tools`. A corresponding version with extension :code:`.cmd`
can be used on Windows operating system. Note that the path to the executable *must not have any spaces*.

**Settings**

* Replay Tool:
    *  Executable: path to the wrapper e.g. :code:`usr/local/rase/tools/FullSpec_replaytool_wrapper.cmd`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`/usr/path/to/full-spec.exe INPUTDIR OUTPUTDIR <DRF_name_here>`
* Sampled Spectra n42 Template:
    *  n42 Template File: none - leave empty
    *  Suffix of input files: .n42
* Identification Results Translator:
    *  Executable: :code:`SandiaWebID-CmdLine_ResultsTranslator.exe`
    *  Command Line checkbox: checked
    *  Command Arguments: :code:`INPUTDIR OUTPUTDIR` [this is a default entry]

For the :code:`<DRF_name_here>` field, the user should supply the name of whichever DRF they would like to use with the detector, with
proper capitalization. The user may review which DRFs are available in the drop-down "Instrument DRF" menu in the "Full Spectrum
Web ID" window of the :code:`Edit Replay Software` menu.

To add custom DRFs, a folder must be added to the :code:`/usr/path/to/fullspec_exe/gadras_isotope_id_run_directory/drfs` directory
which contains the following files:

    * :code:`DB.pcf`
    * :code:`Detector.dat`
    * :code:`Rebin.dat`
    * :code:`Response.win`

As for the web version, spectra supplied to Full Spectrum should contain a secondary background for optimal results.  Please configure
the detector accordingly using the :code:`Edit Detector` dialog.


