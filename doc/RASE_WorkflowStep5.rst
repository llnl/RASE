.. _workflowstep5:

#########################################################################
 RASE workflow step 5: Execute the replay tool and the result translator
#########################################################################

Once you associate a replay tool with the instrument and generate sampled spectra for
a scenario, highlight the instrument/replay combination and at least one scenario in the
main RASE window to enable the :guilabel:`Run Replay Tool` button.

Click the :guilabel:`Run Replay Tool` button to run the replay tool. RASE creates a sub-directory with the
identification report files for each sampled spectrum. This directory also contains the terminal
output from the replay tool, which is useful for troubleshooting. If the replay tool is not
command line-based, RASE launches the external software and you must interact with it
(often by manually specifying sample spectra files to process). If the external tool does not
write its processed files into the replay folder created by RASE, import them back using the
:guilabel:`Import Results...` button.

The :guilabel:`Run Result Translator` button is accessible only via the :guilabel:`Advanced Actions` tab. Most detectors do not
require a separate translator. If a translator is required, RASE runs the translation step
automatically along with the replay step in the standard RASE workflow. Running the translator
automatically (in the standard RASE workflow) or manually (in the advanced actions) creates a third
sub-directory containing identification report files formatted for use by the RASE code.

|

.. _rase-workflowstep5:

.. figure:: _static/rase_WorkflowStep5.png
   :scale: 33 %

   :guilabel:`Run Replay Tool` in main window