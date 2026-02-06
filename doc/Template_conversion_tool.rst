.. _template_conversion_tool:

###################################
Detector template conversion tool
###################################

Use the template conversion tool in the :guilabel:`Tools` menu of the main window to
directly convert one spectrum format to another. It decouples detector hardware
performance from its isotope ID algorithm, allowing you to test a detector response
against different algorithms or versions.

The tool is comprised of a few lines and buttons:

-  Input config file: The same file used by the Base Spectra Creation tool to extract
   spectral data from raw files. RASE includes a pre-configured config file; you can add
   entries to support more file formats.

-  Input template: Select the format to convert from. The
   templates come from the config file.

-  Output template: Define the output file format. These templates are the same as
   those used for scenario generation.

-  Input folder: The directory that holds the spectra to be converted to a different
   format.

-  Output folder: The directory that will hold the converted spectra.

Note that the tool will not convert spectra if the output template requires a field that is not
present in the input spectra. For example, the tool will not allow converting to an output
template with a secondary spectrum if the input template does not also have a secondary spectrum.
Many input templates included in the RASE distribution store secondary spectra (such as
background and calibration spectra) in the "additional" field, which does not satisfy this
requirement; you may need to modify the template configuration file for your files.