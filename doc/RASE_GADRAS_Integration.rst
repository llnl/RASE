.. _rase_gadras_integration:

#############################
 RASE and GADRAS integration
#############################

GADRAS version 19.3.3 provides a Python API,
allowing you to call GADRAS capabilities directly from custom Python scripts.
One useful capability is generating spectra for an instrument described by a detector response
function (DRF), which you can use to supplement a RASE workflow in several ways. For example, you
may want to compare several instruments but lack the base spectra for one of the detectors you are
interested in, or you may have data for an instrument but be missing base spectra for one or
two sources you need. GADRAS can simulate the response for that detector,
and RASE can convert the resulting pcfs into base spectra.

One common use case is replicating the base spectra set of an existing
detector with another detector simulated in GADRAS to compare the two. To support
this, the ``gadras_clone_detector.py`` script is included with the distribution of RASE in the
`tools` folder. Though you must modify or write your own Python script to use it, the
implementation is straightforward. The script contains one function,
``clone_detector_yaml()``, which takes as arguments:

   -  an RASE detector ``.yaml`` file (exported from an existing RASE session)
   -  the path to the DRF for the instrument you want to model
   -  the path to the local GADRAS installation

The function reads the RASE detector ``.yaml`` file, identifies all source names, and
simulate those sources for the DRF you specified. The output detector responses will
automatically be converted into base spectra .n42 files, which you can then load into RASE to
define a detector. The script can only simulate source names it recognizes; for
example, the script will not work if the detector ``.yaml`` file has a source by the name of
"MyPocketCs137," and will simply skip over the source (unless you specify a ``force=True``
argument, in which case the code will crash if it encounters a source name it does not recognize).
Because the script only looks for source names and no other source information, you
are free to modify the source names in the ``.yaml`` file to generate any number of
desired sources.

The spectra are simulated with an assumed standoff of 100 cm. All base spectra are yielded in
units of dose only.