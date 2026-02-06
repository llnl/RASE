.. _workflowoverview:

########################
RASE workflow overview
########################

The overall RASE evaluation workflow is shown in the figure below. The current version of the
software provides end-to-end functionality.

First, define instruments and load their base spectra. Scenarios can then be
defined to reproduce measurement conditions of interest. Generate the synthetic spectra
(sampled spectra) next. After generation, inject them into the instrument replay
tool for analysis. Run the replay inside RASE if you have a command-line
replay tool defined. Alternatively, use a stand-alone replay tool outside of RASE
for isotope identification. Finally, load the identification output into RASE and
inspect it to evaluate the instrument performance.

RASE has been tested to be compatible with about 30 different spectrometric instruments and their
base spectra. Access to the base spectra library is available upon request and requires approval. For
most of the RASE-compatible instruments, a vendor-supplied replay tool has been integrated.

|

.. _rase-workflow:

.. figure:: _static/rase_workflow.png
   :scale: 50 %

   **RASE analysis workflow and functionality.**