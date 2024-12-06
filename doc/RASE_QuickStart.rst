.. _quickstart:

*****************
Quick Start Guide
*****************

Distribution
============

RASE is distributed as an executable; all GUI capabilities can be utilized via the executable. To access the RASE API, the user must have an up-to-date python installation and the most recent RASE codebase, which can be accessed via https://github.com/LLNL/RASE. Example API scripts are found in the :code:`examples` directory.

Pregenerated Workflow Setup
===========================

RASE comes packaged with a preconfigured instrument, list of scenarios, and correspondence table for a user to get started quickly. By following the steps below, the user should be able to have a functional workflow within minutes.


Quick Instrument Setup
----------------------

From the main window, click the "Add Instrument" button to enter the detector dialog. Select "Import Instrument" and load the pre-configured detector file :code:`detimport_genericnai_wfullspec.yaml` from the examples folder. This will load a detector pre-populated with spectra simulated for a generic 2x2 NaI(Tl) detector. It also loads a pre-generated FullSpec WebID replay tool; this must be attached to the detector by clicking the checkbox in the detector window after the information is loaded.

.. figure:: _static/quickstart_Detector.png
    :scale: 65 %

    **Procedure to load in the pre-generated detector distributed with RASE.**

Quick Scenario Setup
--------------------

From the main window, click the "Import from .csv" button near the top right. Select the :code:`ANSI_scenario_import.csv` file and accept: the will populate the scenario list with the ANSI standard for several sources.

.. figure:: _static/quickstart_Scenarios.png
    :scale: 65 %

    **Procedure to load in the pre-generated scenarios distributed with RASE.**

Quick Correspondence Table Setup
--------------------------------

From the main window, select "Setup --> Correspondence Table" to enter the correspondence table dialog. Click the "Import from .csv" button, select :code:`default_corrtable.csv`, and hit accept: this will load the pre-generated correspondence table into RASE. Simply provide a name to save the table as (such as "default") and close the dialog.

.. figure:: _static/quickstart_CorrTable.png
    :scale: 65 %

    **Procedure to load in the pre-generated Correspondence Table distributed with RASE.**

.. quickstart:
