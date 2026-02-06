.. _glossary:

##########
 Glossary
##########

This section provides definitions for key technical terms used throughout the RASE Software User
Manual.

************
 Background
************

Natural radiation or environmental noise measured by the detector when no specific radioactive source
is present. Background spectra are essential for removing unwanted contributions from source
measurements.

**************
 Base spectra
**************

Background-subtracted, high-statistics gamma-ray spectra acquired from individual isotopic sources
with an instrument. These spectra form the basis for generating synthetic spectra and are stored in
the ANSI `.n42` format.

**********************
 Correspondence table
**********************

A mapping used in RASE to relate labels reported by the replay tool to the expected isotopes in a
scenario. Use it to decide whether an identification result is correct or incorrect.

**********************************
 Detector response function (DRF)
**********************************

A mathematical model or data set that describes how a detector responds to radiation across energies.
DRFs are used by simulation tools like GADRAS to generate synthetic spectra.

******
 Dose
******

The radiation dose rate at a specific location (the detector face), typically expressed in units of
`µSv/h`. Dose measures the energy deposited by ionizing radiation in a medium and is used to assess
effects on the detector or environment.

************
 Dwell time
************

The duration, in seconds, of a measurement or simulation; effectively the time the detector is
exposed to the source.

******
 Flux
******

The number of gamma rays passing through a unit area per unit time, typically expressed in units of
`gammas/cm²/s`. Flux quantifies radiation intensity at the detector face and is often associated with
a characteristic photopeak.

**************
 ID algorithm
**************

An isotope identification algorithm that analyzes gamma-ray spectra to detect specific radioactive
isotopes. ID algorithms use techniques such as peak matching, template fitting, or statistical
analysis and run in replay tools; they vary in complexity and accuracy.

***********
 Influence
***********

A perturbation applied to sampled spectra to mimic environmental effects like temperature changes,
detector bias shifts, or electromagnetic interference. Influences are defined by mathematical
coefficients and resolution distortion terms.

***********************
 Instrument (detector)
***********************

A spectrometric device that measures radiation and produces spectra. In RASE, define instruments by
their base spectra, replay tools, and associated settings.

******************
 Intrinsic source
******************

A weak radioactive source inside the detector, typically used for continuous energy-scale
calibration to stabilize against drift from environmental or electronic changes.

**********
 Material
**********

A substance or source defined in RASE scenarios, typically representing isotopes, radioactive
sources, or background radiation. Materials can be specified in units of dose rate (µSv/h) or flux
(gammas/cm²/s) and link to base spectra for simulation.

**************
 n42 template
**************

A template file in the ANSI N42.42 format that RASE uses to generate synthetic spectra matching the
vendor-specific format so they are compatible with the corresponding replay tool. The template
defines the `.n42` file structure and includes python tags processed by RASE.

*************************************
 Probability of identification (PID)
*************************************

A metric that quantifies the likelihood that one or more isotopes in a scenario are correctly
identified by the instrument or replay tool.

*************
 Replay tool
*************

A standalone program, often provided by the instrument manufacturer, that analyzes gamma-ray spectra
and identifies isotopes. Replay tools can be GUI-based or command-line executables.

*************
 Replication
*************

The number of different but statistically compatible synthetic spectra generated for a scenario
during a simulation. Replications enable statistical analysis of instrument performance.

*******************
 Result translator
*******************

A program or tool that converts replay tool output into a format RASE can analyze. Use translators
when replay tool outputs are not natively supported by RASE.

*********
 S-curve
*********

A sigmoid-shaped curve that shows the relationship between isotope identification performance and
source intensity. Use it to evaluate identification thresholds and ID algorithm performance.

*****************
 Sampled spectra
*****************

Synthetic gamma-ray spectra produced by down-sampling and combining base spectra to simulate data
acquisition under varying dose rates, fluxes, and acquisition times.

**********
 Scenario
**********

A RASE simulation setup that defines the combination of sources, background materials, acquisition
times, and other parameters used to generate synthetic spectra for analysis.

********************
 Secondary spectrum
********************

An additional spectrum included with base or sampled spectra that represents background radiation,
an internal calibration source, or other secondary contributions to measured data.

*************************
 RASE sensitivity factor
*************************

A scaling factor that links the net count rate of a base spectrum to the gamma source intensity
(dose and/or flux) during acquisition. It enables simulating spectra at different intensities and
acquisition times.

********
 Source
********

A radioactive material or isotope used in measurements or simulations. Sources are defined by their
radiation emission properties.