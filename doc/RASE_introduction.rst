.. _introduction:

##############
 Introduction
##############

The Replicative Assessment of Spectrometric Equipment (RASE) methodology is a semi-empirical
approach for generating synthetic gamma-ray spectra to inject into a radionuclide identification
algorithm of a vendor-provided radiological detection system. RASE supports studies of the
spectroscopic device performance and provides a quantitative assessment of its ability to correctly
distinguish and identify isotopes of interest in simulated scenarios. Using this methodology
reduces the need for full-scale experimental tests and permits investigation of hard-to-implement
measurement situations. Because RASE is semi-empirical, the approach lets you factor in physical
effects on the spectrometer response, such as detector package construction, and external
influences (temperature, EMI, count rate, etc.). This is achieved by acquiring a set of high-accuracy
base spectra from individual isotopic sources using an actual instrument. You can then down-sample
and combine these spectra to generate large sets of synthetic spectra (called sampled spectra)
that simulate data acquisition at a variety of dose rates/fluxes and dwelling times.

The RASE methodology is described in detail in :cite:`RASE_IEEE`. Some validation of the
methodology is reported in :cite:`RASE_validation`. Additional validation work is ongoing. The
RASE software described in this manual implements the RASE methodology in an intuitive and
user-friendly interface.

Please contact the LLNL development team at rase-support@llnl.gov with any feedback, bug reports,
observations, and recommendations.