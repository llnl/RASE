.. _results_format:

#############################################
 Identification results file format for RASE
#############################################

The following guidelines ensure that identification result files produced by
replay tools are natively compatible with RASE. You can also use them to develop a
translator to convert native replay tool output to the RASE format.

The file name for the output file containing identification results from the replay tool must match
the input sample spectrum, with the extension changed to ``.res``. For example, the file named
``Vabcd_M123_S80FBDC_04.res`` contains identification results for the sample spectrum named
``Vabcd_M123_S80FBDC_04.n42``.

The data in identification results files must use ASCII characters.
Encapsulate the data using the extensible markup language (XML), which makes the file self-describing.
The file must list the isotopes identified and their corresponding confidence index,
which measures how reliable each isotope identification is.
Express the confidence index as a number from 1 to 10 that indicates the degree of certainty.

An example of the identification result file is given below:

.. code:: XML

   <?xml version="1.0" encoding="UTF-8"?>
   <IdentificationResults>
        <Identification>
             <IDName>K-40</IDName>
             <IDConfidence>9</IDConfidence>
        </Identification>
        <Identification>
             <IDName>Ra-226</IDName>
             <IDConfidence>4</IDConfidence>
        </Identification>
        <Identification>
             <IDName>U-238</IDName>
             <IDConfidence>8</IDConfidence>
        </Identification>
   </IdentificationResults>

A legacy format is also acceptable. In this format, identifications are provided as a
newline-separated list of
identification labels followed by a newline-separated list of confidence indices, as in the
following example:

.. code:: XML

   <?xml version="1.0" encoding="UTF-8"?>
   <IdentificationResults>
        <Isotopes>
           K-40
           Ra-226
        </Isotopes>
        <ConfidenceIndex>
           4
           8
        </ConfidenceIndex>
   </IdentificationResults>
