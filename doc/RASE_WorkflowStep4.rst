.. _workflowstep4:

################################################
 RASE workflow step 4: Generate sampled spectra
################################################

Confirm the desired instruments and scenarios are present and correctly specified in the
appropriate tables. To modify or delete an entry in the "Scenarios" or "Instruments" table,
double-click the row or use the context menu.

At this point, generate sampled spectra by executing these steps:

#. Select one or more entries in the "Instruments" table
#. Select one or more entries in the "Scenarios" table
#. Choose one of two routes to proceed through the workflow execution:

   #. Press the "Gen Sampled Spectra" button that becomes available to generate the sampled
      spectra.

   #. Press the "Run Scenario" button that becomes available to sequentially execute the
      entire workflow (generate sample spectra, run replay, and run translator) for all selected
      scenarios and instruments without further input. This option only becomes available if all
      selected instruments have command line-based replay tools.

   The rest of this guide assumes you selected option (a) and will execute the steps manually.
   The workflow ends in the same place whether you use option (a) or option (b).

If a selected instrument has no base spectra for materials present in the scenario, the "Gen
Sampled Spectra" and "Run Scenario" buttons remain unavailable. The missing materials for the
instrument will be highlighted red in the "Scenarios" table.

To view generated sample spectra, select a detector and a scenario, right-click the scenario to
open the context menu, and choose the appropriate option. "View Sample Spectra" shows individual
spectra; "View Summed Sample Spectra" shows all replications summed together.

Open the directory containing the sampled spectra by pressing the "Sample Spectra Dir" button. If
an n42 template file was specified in the replay tool settings associated with the current
instrument, a second directory will also be present that contains the sampled spectra formatted
for injection into the specified replay tool.

Access the directory containing data for a specific scenario from the context menu in the
"Scenarios" table. An instrument must be selected for this option to become available.

******************************************************************
 Advanced actions: Importing sample spectra and experimental data
******************************************************************

Enable advanced actions by checking the "Enable advanced actions" checkbox. Two buttons appear
next to the "Generate Spectra" and "Run Replay Tool" buttons: "Import Spectra" and
"Import Replay Results".

To import experimental spectra for comparison with simulated data, select a detector and a
scenario, then click "Import Spectra". In the directory dialog, navigate to the folder that
contains the spectra and click "Okay". RASE imports the spectra and treats them the same as
spectra generated within RASE. You can import experimental spectra for one detector and simulate
spectra for another to compare replay results. RASE does not mark scenarios or detectors that
have imported spectra; keep track of these yourself. You do not need a separate instrument for
experimental spectra: imported and sampled spectra may coexist under a single instrument.

RASE does not verify the correctness of imported spectra. You must confirm that live times,
dwell times, dose rates, etc., match the scenario setup. Also confirm that the imported spectra
are compatible with the replay tool in the same manner as spectra generated in RASE. RASE does
not check that the number of imported spectra equals the number of replications defined for a
scenario, but if the number of replications exceeds the number of imported spectra the workflow
should operate normally and correctly.

|

.. _rase-workflowstep4:

.. figure:: _static/rase_WorkflowStep4.png
   :scale: 33 %

   **Populated main RASE window showing how to generate sample spectra.**