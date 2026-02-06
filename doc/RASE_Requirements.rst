.. _requirements:

###############################
 Requirements and installation
###############################

**************
 Requirements
**************

RASE is intended to run on mainstream platforms and operating systems.
The binary executable runs on Windows 7 and 10 without an installation procedure,
downloading additional libraries, or requiring administrator permissions. RASE is coded in Python
and can be compiled to run also on macOS or Linux operating systems.

In order to effectively utilize all functions of the RASE software, the user must have access to the
following additional files and utilities:

-  **Base spectra** for the instruments under evaluation. Define the base spectra in the
   \*.n42 format and follow the RASE standard requirements. See :ref:`create_base_spectra`.
   The current library of base spectra is not included with the RASE distributable version and
   should be requested separately. A set of example NaI base spectra is provided with the distributable
   for workflow testing and demonstration.

-  **Replay tools**: stand-alone programs that replicate the radioisotope identification
   software deployed on the instrument. These are generally provided by the manufacturer and can be
   executed from the command line or via a native graphical user interface. A demo replay tool is
   provided with the RASE distributable version for testing purposes.

-  **Instrument-specific n42 templates** used by RASE to generate sample spectra in the
   native format required by the vendor replay tool. See :ref:`n42_templates` for details on creating a
   template for a new instrument. Templates for some compatible instruments are provided with the
   RASE distributable version.

-  **Results translators**: an executable that converts replay tool outputs to a format
   compatible with RASE. If the replay tool output is already in RASE format, a results translator
   is not required. Translators for some instruments are included with the RASE distribution, and RASE
   automatically translates the output of many replay tools. If you need a translator for a specific
   instrument or replay tool, contact the RASE developers.
   Details on the format of the identification results files are provided in :ref:`results_format`.

**********************************
 Installation and getting started
**********************************

To get started quickly with a functional workflow, see the :ref:`quickstart`.

-  Create a dedicated directory for RASE, and place the RASE executable and the enclosed directories
   inside it.

-  Make sure that the following subdirectories (names are arbitrary), and the appropriate content
   are present along with the executable:

      -  subdirectory for base spectra;
      -  subdirectory for replay tools;
      -  subdirectory for the correspondence table and its versions;
      -  subdirectory for translators;
      -  subdirectory for shielding modules.

-  On first run, navigate to the :menuselection:`Setup --> Preferences` menu and set the :guilabel:`RASE Data Directory` field to a working
   directory where you want RASE to store output results. Then close and restart RASE for the
   change to take effect.

-  The software will automatically create a subdirectory in the working directory named
   "SampledSpectra" where all synthetic data and analysis results will be located as well as a
   "SampledSpectra_View" directory, which mirrors the content of "SampledSpectra" with human-interpretable
   file/directory names.


-  Clicking the :guilabel:`Sampled Spectra Dir` button in the main window opens its content in a separate OS file
   explorer window.

-  You must have a correspondence table to view isotope identification results. An empty
   correspondence table (just a name and no content) is sufficient to start the analysis.
   Navigate to the :menuselection:`Setup --> Preferences` dialogue and create a table or select an existing one.

-  RASE stores its database in a sqlite file inside the RASE data directory. Do not delete or
   modify this file.

-  A human-readable log text file "rase.log" will be created in the working directory. It records
   only information about errors encountered during code operation. Include this file when reporting
   errors to the RASE developers.

..
   rase_requirements: