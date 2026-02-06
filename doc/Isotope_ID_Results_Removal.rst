.. _isotope_id_results_removal:

#######################################
 Isotope ID Results Removal Tool
#######################################

Use the Isotope ID Results Removal tool, located in the "Tools" menu of the main window, to
create copies of .n42 or .xml measurement files with embedded isotope ID results removed. This
helps validate replay tools by ensuring output files do not contain residual results from the
fielded instrument's algorithm. Note that the original files remain unaffected.

Specify an input directory and an output directory. The tool scans the input
directory for .n42 or .xml files, copies each file, and removes any embedded isotope ID results
(if present). Save the ID-less copies to the output directory, preserving the same
subdirectory structure as the input directory. Files without isotope ID results are copied as is.
Additionally, the tool generates a text file in the output directory that lists all files
that were copied without modification.

Import the ID-less files into RASE's "Import Spectra" functionality to evaluate them with the
associated replay tool. To analyze the spectra with a different replay tool, use the retemplating
tool (see :ref:`template_conversion_tool`). The retemplating tool also removes isotope ID results while
converting the spectrum format.

Advanced users can also access the ID results removal functionality via the API.