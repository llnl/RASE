.. _weightsTable:

******************************
Weighted f-score calculations
******************************

RASE computes statistics from scenario results, including True Positive (Tp), False Positives (Fp), False
Negatives (Fn), Precision, Recall, and F-Score.
RASE also computes weighted versions of these quantities. The weighted calculation follows the prescriptions
and methodology from :cite:`AIP`.

Use the *Weighted F-Score Manager Dialog* to define each material's weights. Use the same dialog to enable
RASE's processing of identification confidences when the replay tool provides them. When viewing results, the
weighted and unweighted values are both calculated and shown in the table; weighted columns are labeled with a
"w" before the statistic (e.g.: weighted Tp is noted as wTp, weighted precision is noted as wPrecision, etc).

Open the weights table from the "Setup" menu in the main window by selecting the "Weighted F-Score Manager..."
option. Like most other tables in RASE, the material
weights table can be imported from and exported to .csv files using the "Import from csv" and "Export to csv"
buttons in the material weights table dialog. The table can also
be accessed from the results table; results update automatically to reflect changes to the weights table (the
same behavior as when the correspondence table is edited).

Using the Material Weights Table
================================

To use identification confidences reported by many instrument replay tools when calculating weighted ID
statistics, check the "Use isotope
ID confidences..." checkbox. RASE looks for confidence values given either as a text rating "low", "medium",
or "high", or as a number between 0–10.
If the confidence is "low" or a number between 0–3, isotope IDs receive a weight of 1/3. If the confidence is
"medium" or a number between 4–6, assign
weight 2/3. If the confidence is "high" or a number between 7–10, assign weight 1. If you enable this option
but the replay
tool output contains no confidence values, all IDs get a default weight of 1. Note that only the weighted
versions of these statistics are affected. ID
confidence does not affect the weighted Fn rate, because the isotope was not identified and therefore has no
confidence.

The material table lets you specify unique Tp, Fp, and Fn importance weights for materials. To have the
weighted F-score include these material weights,
check the "Use specified material weights..." box. Materials appear as selectable in drop-down
boxes in the "materials" column if they have already been imported as base spectra for a detector. If you
assign an importance weight, RASE applies it
to weighted statistics regardless of whether the material appears in the scenario; this allows user-specified
weights to affect false
positives. If a material is not specified in this table, RASE treats its Tp, Fp, and Fn importance weights as
1, so it contributes the
same amount as in the unweighted calculations.

Material weights table interaction with the correspondence table
================================================================

Materials in the weights table follow the same material-identification logic defined by the correspondence
table. Weights do not affect isotopes
specified as "Allowed IDs" in the correspondence table when that material appears in the scenario; these IDs
do not affect the weighted Tp, Fp, or Fn values calculated for a scenario.

If you specify a material<->ID equivalency in the correspondence table multiple times, and those multiple
materials are included in a scenario, and
the ID associated with them is identified, RASE uses the largest weighting factor for each term. For example:
"Uranium" is defined as a correct
ID for "DU" and "HEU". If you define a scenario that includes both DU and HEU, and the replay tool identifies
"Uranium", RASE uses the higher Tp of the two materials
as the Tp weight; it does the same for Fp and Fn. RASE determines the maximum separately for each weighting
factor.


An example of weighting
=======================

Define a single-replication scenario that includes HEU and WGPu. Use the table to specify importances (Tp, Fp,
Fn) of (4, 2, 3) for HEU and
(1, 2, 0.5) for DU, and do not explicitly specify WGPu. Also check the box that allows confidences to be used
in weighted calculations. The replay tool
identifies WGPu with confidence 9 and DU with confidence 2. The unweighted results are Tp = 1 (correctly ID'd
WGPu), Fp = 1 (wrongly ID'd DU),
and Fn = 1 (failed to ID HEU). The weighted results are wTp = 1 (WGPu was correctly identified; since you did
not set a weight for it, its Tp weight defaults to 1, and
it was identified with confidence 9 ("high"), giving confidence weight 1: 1 * 1 = 1), wFp = 0.667
(you provided an Fp weight of 2 for DU, and it was ID'd with confidence 2 ("low"), so its confidence weight is
1/3: 2 * 1/3 = 0.667), and wFn = 3
(you provided an Fn weight of 3 for HEU; because HEU was not identified, it has no ID confidence). If you run
more replications, the results will be averaged across all replications.

|

.. figure:: _static/WeightsTable.png
    :scale: 60 %

    **"Material Weights Table" dialog, accessible from the "Setup" menu in the main RASE window.**