.. _correspondencetable:

#################################################
 Correspondence table for identification results
#################################################

The correspondence table specifies which isotope identification results count
as success or failure for a given scenario, affecting the score of an identification
algorithm (or replay tool). For example, if an isotope in a scenario is background and
does not need to be identified for a test to succeed, or if an identification result of
“HEU/LEU” counts as a success for HEU, edit the correspondence table to
reflect these choices. In short, the correspondence table provides the interpretative logic
between the material labels defined in RASE scenarios and the identification labels in
the replay tool output.

The correspondence table can be managed using the dedicated window accessible under the “Setup”
menu. Use the window to add entries manually, or to import and
export the table in comma-separated \*.csv format. \*.csv files can also be edited in Microsoft
Excel outside the RASE software.

RASE provides a default correspondence table in the fixtures.py file, which can be found on
github.com/LLNL/RASE. Future versions of RASE will include this table by default.

.. figure:: _static/CorrTable.png
   :scale: 75 %

   **"Correspondence Table" dialog, accessible from the "Setup" menu in the main RASE window.**