.. _workflowStep3:

************************************************************
RASE Workflow Step 3: Define the Replay Tool and Translators
************************************************************

NOTE. This step is not required to generate populations of sampled spectra with the RASE code. The user can skip this step, generate scenarios and sampled spectra, and define the replay tool later.

Before the "Run Replay Tool" button on the main window can be activated, the instrument must have at least one replay tool associated with it.

Two types of isotope identification algorithms can be used in the RASE workflow:

*  Standalone replay tools (usually provided by an instrument's vendor), which come in two types:

  * Command-line executable, which can be configured for automated execution with RASE

  * GUI-based replay tool, which needs manual user interaction outside of RASE

*  Full-Spectrum Web ID, developed by Sandia National Laboratories, which can be accessed directly by RASE by providing the web address.

For standalone replay tools, the user must also specify an instrument specific n42 template and a identification results translator in order to ensure compatibility of the RASE file formats with instrument-specific spectral and replay tool output files.
See :ref:`requirements` for more details on these.
The user should be aware of the instrument manufacturer's instructions on replay tool operation and the command line syntax requirements. For convenience, some example of configuration settings for replay tools are provided in :ref:`replayToolSettings`.
If necessary, these may be provided by the RASE code developers, and may require specific settings.


To define a standalone replay tool:

*  Double-click on an entry in the “Instruments” table.

* In the “Edit Instrument” window, click the “Add New” button near the “Associated Replays” field.

*  In the “New Replay Software” dialog that opens, choose "Standalone Executable"

* Use the “Browse” button to navigate to the command line replay tool executable. Make sure that the “Command line” checkbox is selected.

*  In the “Replay Settings:” field, type in the command line parameters (obligatory). The RASE software will automatically substitute the INPUTDIR and OUTPUTDIR entries with the path to the directories where the sampled spectra and replay tool results are located.

*  Similarly, use the "Browse" buttons to identify the path to the “Replay Tool n42 Input Template” and the “Replay Results Translator.”

If the user has access to Full Spectrum Web ID, it can be used as an alternative identification algorithm by selecting the corresponding checkbox in the "New Replay Software" dialog, and then entering the web address :code:`https://full-spectrum.sandia.gov/` and selecting the appropriate instrument in the combo box. 

Once a replay tool is defined, it needs to be associated with an instrument. Instruments can have more than one replay tool associated with them, and the same replay tool can be used by different instruments. This is useful for example when comparing performance of different versions of a replay tool or comparing different replay tools as the underlying spectra will be kept identical between replays associated with the same instrument.

The association between replay tools and instruments is performed by selecting the check-box next to the replay name in the table of "Associated Replays" that is displayed on the left side of the "Add/Edit Instrument" dialog.

For instruments with associated replay tool, the “Run Replay Tool” and "Run Results Translator" buttons become available in the RASE main window.
The “Instruments” table in the main window have one entry for each replay tool associated with each instrument.

Replay tool settings can be edited at any time by double-clicking the replay tool name in the “Instruments” table.

Confidences
===========

Replay tools often return confidence values associated with each identified isotope. These values typically range from 0-1, 0-10, or 0-100, but can also be discrete values such as "low," "medium," and "high." These factors can be incorporated into the weighted statistics calculations RASE yields, such as "weighted True Positive" and "F-score." Using confidences in the weighted calculations is toggled in the "Weighted F-Score Manager," which can be accessed from the tools menu of the main GUI. For more details on that window, see  :ref:`weightsTable`.

The left column of the confidence weighting table is what the replay tool reports. The right side are the weights that are assigned to them for RASE statistics calculations. Weights (the right column) always must be within a range of 0-1, inclusive.

RASE is able to incorporate both continuous and discrete confidences into its calculations, and has default settings for both. For discrete, it expects the "low," "medium," and "high" flags, and assigns them weights of 0.333, 0.667, and 1, respectively. For continuous, RASE assumes confidences range from 0-10 and maps a 0-1 weight linearly across this range. The user can modify these freely from the GUI accessed from the replay tool menu.

Discrete settings are always 1:1 in terms of "reported value" to "RASE weighting value." The user can add as many reported values and associated weights as is desirable. For continuous, the user must define points that are monotonically increasing in the left column and *either* static or monotonically increasing in the right. RASE will then interpolate between the list of points to assign weights to reported confidences. If, for example, the user supplies "0, 3, 8, 10" in the left column  and "0, 0, .5, 1" in the right column, RASE will assign a weight of 0 to any IDs with a confidence less than 3, then will linearly increase in assigned weight from 0 to 0.5 across the reported range of 3 to 8, and finally will linearly increase from 0.5 to 1 across the reported confidence range of 8-10.

Each replay tool has unique confidence treatment settings. It falls to the user to understand the confidence reporting regime of the replay tool they are using.


.. _rase-WorkflowStep3:

.. figure:: _static/rase_WorkflowStep3.png
    :scale: 70%

    **“Define Replay Tool” dialog.**

.. _rase-replayConfidences:

.. figure:: _static/rase_ReplayConfidences.png
    :scale: 70%

    **Discrete and Continuous Replay Confidences dialogs.**
