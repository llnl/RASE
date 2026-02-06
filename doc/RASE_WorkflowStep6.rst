.. _workflowstep6:

####################################################
 RASE workflow step 6: Replay tool results analysis
####################################################

**************
 View results
**************

Click the "View Results" button to open a summary table of the replay tool results for the
selected instrument and scenario combination. If you select multiple scenario/instrument/replay
combinations, the Results button remains enabled as long as at least one selected combination has
results ready to view. Customize the number of columns shown in the View Results dialog via the
table settings dialog using the :guilabel:`Table Settings` button. You may also edit the correspondence table
with the :guilabel:`Correspondence Table` button; changes update the results table live. If a material name uses the
format XXnnn (for example, Rn226, K40) and the material is defined as a source, RASE will match
both "XX-nnn" and "XXnnn" when computing results (for example, if Cs137 is defined, RASE treats
Cs-137 and Cs137 as equivalent "correct IDs"). RASE does not apply this equivalence for materials
defined as background entries (so Cs137 and Cs-137 count as distinct identifications). For
background materials, enforce equivalence manually and on an isotope-by-isotope basis in the
correspondence table.

**Detailed identification results** for each individual spectrum open by double-clicking the row of
interest in the :guilabel:`View Results` table. Use detailed results to find spectra that produced unexpected
outputs or to decide how to adjust correspondence table comprehensions for a specific study. Use
:kbd:`Ctrl+C` or right-click to copy ID results, then paste the exact entries to update the
correspondence table comprehensions.

For each scenario, RASE also computes the **frequency of identification results** across all generated
samples. Access this analysis by right-clicking an entry in the :guilabel:`View Results` table and selecting
the :menuselection:`Show Identification Results Frequency` menu.

The tables in the :guilabel:`View Results` and :guilabel:`Detailed Results` dialogs can be exported as a :file:`*.csv` file and
opened in Excel for plotting and further analysis. You can also review RASE-generated sampled
spectra and replay-tool outputs manually with programs like PeakEasy and Interspec.

|

.. _rase-workflowstep6a:

.. figure:: _static/rase_WorkflowStep6.png
   :scale: 33 %

   **Main RASE window showing how to access identification results dialogs**

|

.. figure:: _static/rase_WorkflowStep6-2.png
   :scale: 33 %

   **"View Results" and "Detailed Results" tables.**

|

RASE evaluates identification performance using both unweighted and weighted F-score methods based
on the geometric mean of precision and recall. For more details on the F-score see :cite:`AIP`.

RASE computes confidence intervals using the Wilson score method. Wilson score intervals are
asymmetric and biased towards 0.5, but they typically provide more accurate intervals than "exact"
methods such as Clopper-Pearson, which are often overly conservative (see Newcombe, 1998).

Each term in the View Results table is calculated independently for every sample spectrum, then
averaged across all replications for a scenario. The column definitions are:

.. math::

   Prob_{\text{ID}} = \begin{cases}
                        1, & \text{if all isotopes are correctly identified}\\
                        0, & \text{otherwise}
                      \end{cases}

.. math::

   {\text{CIs (for both } Prob_{\text{ID}} \text{ and } C\&C)} = {\text{Upper and lower confidence interval
   bounds for a given } \alpha}

.. math::

   {\text{True Positives}} = \frac{\text{number of true positives}}{\text{total number of sources in
   scenario}}

.. math::

   {\text{False Positives}} = {\text{Number of identified isotopes that were not defined in the scenario
   sources}}

.. math::

   {\text{False Negatives}} = {\text{Number of isotopes defined in the scenario sources that were not
   identified}}

.. math::

   C\&C {\text{ (Complete \& Correct)}} = \begin{cases}
                                        1, & \text{if all sources are correctly ID'd with no false positives}\\
                                        0, & \text{otherwise}
                                        \end{cases}

.. math::

   Precision = \frac{\text{number of true positives}}{\text{(number of true positives) + (number of false
   positives)}}

.. math::

   Recall = \frac{\text{number of true positives}}{\text{(number of true positives) + (number of false
   negatives)}}

.. math::

   F_{\text{Score}} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision + Recall}}

**********
 Plotting
**********

RASE provides built-in one-, two-, and three-dimensional plotting. In the bottom-left of the
:guilabel:`View Results` window, choose result columns from the drop-down boxes to build plots. Selecting only
an x-axis variable produces a histogram of that column. Selecting both x and y variables creates a
2D plot. Choosing a z variable produces a heat map showing that column as a function of the x and
y columns. If you pick source/background dose or flux as an axis, RASE prompts you to choose which
source/background isotope to plot. The :guilabel:`Category` option lets you split results into categories.
For example, choose :guilabel:`Detector` as a category to plot pID vs Source Dose; if the results table
contains multiple detectors, each detector plots in a different color. Click :guilabel:`View Plot` to open
the plotting dialog and display the selected data.

S-curves
========

The plotting dialog supports S-curve fitting. Choose the dataset (or category) to fit and set the
ID-threshold percent for estimation. Press :guilabel:`Plot S-Curve` to fit a sigmoid trendline, when possible.
The fit uses a Boltzmann Sigmoid function:

.. math::

   y_{Fit} = a_2 + \frac{a_1 - a_2}{1 + e^{-(x-M)/B}}

The fit works for curves where identification rate increases or decreases with source intensity. If
the fit succeeds, RASE plots the S-curve with a 1-sigma confidence band and marks the point where the
trendline crosses the ID threshold (the default is 80%, adjustable by the user). The x-value of that
crossing appears in the legend. Toggle these graphical features on or off. Detailed fit results
appear in the text box to the left. Although the fitting algorithm is robust, you may need to adjust
fit parameters manually to aid convergence. Access fit parameters for each curve via the
:guilabel:`Edit S-Curve Fit Parameters` button. You can edit plot properties such as title, axis labels, and scales, and export
the plot to your preferred image format.

|

.. figure:: _static/rase_WorkflowStep6-3.png
   :scale: 33 %

   **Plotting interface and S-curve fits**

|

3D plotting - heat maps
=======================

Heat maps require exactly one result at each grid intersection defined by the x and y variables.
For example, if you define permutations with source A at dose rates 0.1, 0.2, and 0.3 :math:`{\mu}`\ Sv/hr
and source B at 0.4, 0.5, and 0.6 :math:`{\mu}`\ Sv/hr (nine scenarios), you can create a continuous
heat map. If you add a scenario with source A = 0.1 :math:`{\mu}`\ Sv/hr, source B = 0.4 :math:`{\mu}`\ Sv/hr,
and source C = 0.7 :math:`{\mu}`\ Sv/hr (ten scenarios), the heat map fails because a duplicate grid
intersection already exists for source A = 0.1 :math:`{\mu}`\ Sv/hr and source B = 0.4 :math:`{\mu}`\ Sv/hr.
If instead you omit, for example, the scenario with source A = 0.2 :math:`{\mu}`\ Sv/hr and source B = 0.3
:math:`{\mu}`\ Sv/hr (eight scenarios total), the heat map will have an undefined region where that
grid point is missing.

To simplify exploration, enable the :guilabel:`Ignore isotopes with zero contribution` checkbox when you plan to examine several
permutation sets in succession. For example, suppose you create three permutation sets of nine
scenarios each:

   -  Set 1:

         -  source A at dose rates 0.1, 0.2, and 0.3 :math:`{\mu}`\ Sv/hr
         -  source B at dose rates 0.4, 0.5, and 0.6 :math:`{\mu}`\ Sv/hr

   -  Set 2:

         -  source A at dose rates 0.1, 0.2, and 0.3 :math:`{\mu}`\ Sv/hr
         -  source C at dose rates 0.7, 0.8, and 0.9 :math:`{\mu}`\ Sv/hr

   -  Set 3:

         -  source A at dose rates 0.1, 0.2, and 0.3 :math:`{\mu}`\ Sv/hr
         -  source D at dose rates 1.0, 1.1, and 1.2 :math:`{\mu}`\ Sv/hr

If you attempt to create a heat map with the x axis as the :guilabel:`Source Dose` of source A and the y axis
as the :guilabel:`Source Dose` of source B, the map fails because RASE implicitly assumes sources C and D also
exist in those scenarios with dose rate 0. Check the :guilabel:`Ignore isotopes with zero contribution` checkbox to ignore those implicit
zero-dose sources when creating the heat map. This lets you quickly examine all three sets.

.. _rase-workflowstep6b:

.. figure:: _static/rase_WorkflowStep6-4.png
   :scale: 100%

   **An example of plotting three-dimensional data as a heat map.**