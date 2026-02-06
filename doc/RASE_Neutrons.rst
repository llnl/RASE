.. _neutrons:

#####################
 Neutron simulations
#####################

************
 Capability
************

RASE ingests base spectra that include neutron data and uses that data to simulate neutron
detection in scenarios.

RASE can:

#. Load RASE base spectra containing neutron gross count information.
#. Create instruments that include these base spectra.
#. Create scenarios that include neutron-emitting sources and ambient background neutrons.
#. Simulate combinations of instruments and scenarios, computing the expected gross
   neutron counts and simulating random fluctuations for each replication.
#. Place simulated neutron results into a manufacturer-specific output format using RASE's
   template system.

RASE cannot:

#. Simulate neutron spectra. RASE only works with neutron gross counts.

#. Predict neutron emission intensity from a source using its gamma emission intensity (flux or
   dose). You must supply the emitted neutron flux for the scenarios you wish to simulate.

#. Automatically produce neutron-containing base spectra from detector records in a
   manufacturer-specific format. You must add neutrons to base spectra manually (this feature
   may be added in a future update).

***********************
 Creating base spectra
***********************

Starting with a RASE base spectra created following the instruction in ``<GrossCounts id="neutrons">``,
users can add information about the instrument's neutron detection capabilities:

.. code::

   <RadMeasurement id="Foreground">
     <MeasurementClassCode>Foreground</MeasurementClassCode>
     <RealTimeDuration>PT...S</RealTimeDuration>
     <Spectrum>
       <LiveTimeDuration Unit="sec">PT...S</LiveTimeDuration>
       <ChannelData> ... </ChannelData>
       <RASE_Sensitivity> ... </RASE_Sensitivity>
       <FLUX_Sensitivity> ... </FLUX_Sensitivity>
     </Spectrum>
     <GrossCounts id="neutrons">
       <CountData> 75 </CountData>
       <neutron_Sensitivity>0.315</neutron_Sensitivity>
     </GrossCounts>
   </RadMeasurement>

As illustrated by this example, add neutron information to a base spectrum by:

#. Add a ``<GrossCounts id="neutrons">`` block as a child of ``<RadMeasurement>``.

#. In this block, include ``<neutron_Sensitivity>``, listing the neutron sensitivity factor of this
   source, calculated as described below.

#. This block may optionally include a ``<CountData>`` entry. This value is NOT used during any RASE
   calculations, but may be used as a reminder of the neutron measurement that was used to calculate
   the neutron sensitivity.

A base spectrum should also contain gamma detection results. For a pure neutron source, the
``<RASE_Sensitivity>`` should be set to zero. Most neutron-emitting sources produce gammas, so gamma and
neutron information are combined into a single base spectrum file for a source.

Calculating the neutron sensitivity factor
==========================================

The neutron sensitivity factor is calculated in a similar manner as the gamma sensitivity
factor: neutron count rate in the measured spectrum divided by the ground truth neutron flux (in
units of neutrons / :math:`\text{cm}^2-s`) at the face of the detector. This is often difficult
to measure empirically; instead you can calculate it using known source activities and
the solid angle of 1:math:`text{cm}^2` at the measurement standoff.

.. math::

   S_{\text{neutron}} = \frac{ \text{(net measured neutron counts [n])}/\text{(livetime [s])}}{\text{(neutron flux at measurement location} [\text{n}\text{/cm}^2\text{s}])}

In other words:

.. math::

   S_{\text{neutron}} = \frac{4 \pi \cdot  (\text{source-instrument distance [cm]})^2 \cdot \text{(net measured neutron counts [n])}}{\text{(source activity [n/s])} \cdot \text{(livetime [s])}}

This sensitivity factor has units of :math:`\text{cm}^2`.

NB: the flux calculation depends on the neutrons emitted by the source and the surface area of
the sphere where those neutrons reach the instrument. The face area of the instrument does not enter
into this calculation.

In the above example, the sensitivity factor of 0.315 corresponds to 75 neutrons measured from a 1e6
neutrons/s source measured at 2 m for 120 seconds.

Estimating the neutron emission rate for an experimental test source can be challenging. RASE users
are encouraged to reference calibration data provided with their sources or to calibrate the sources
themselves.

As a special case, an ambient background measurement should record the neutron sensitivity factor as
if the ground truth neutron flux were 1, because the actual ground truth flux cannot practically be
estimated for an ambient neutron background. In other words:

.. math::

   S_{\text{neutron background}} = \frac{\text{net measured neutron counts [n]}}{\text{livetime [s]}}

A consequence of this decision is that during scenario creation (described below), ambient neutron
backgrounds are specified as a scaling factor relative to the measurement, e.g., 1x or 2x.

*********************
 Instrument creation
*********************

Creating a RASE instrument with neutrons only requires providing that instrument with base spectra
created as described above. No other changes to the usual procedure are required.

*******************
 Scenario creation
*******************

When creating a RASE scenario, if any instruments use neutron-containing base spectra, the scenario
creation window will contain a column for "Neutron Intensity." When adding a material to a scenario,
specify a neutron intensity for that material.

Any material with nonzero neutron intensity in the scenario and nonzero neutron measurement in its
base spectrum will cause neutrons to be simulated.

Providing a neutron intensity to a material with no neutrons in its base spectrum will result in
zero neutrons in the result. This occurs when simulating an instrument without neutron
detection capability, which will not detect neutrons in the RASE simulation even when
neutron-emitting sources are present.

Calculating neutron intensity
=============================

The neutron intensity of a material in a scenario is its emitted neutron flux. For example, a source
emitting 1e6 neutrons / s observed from 2 m away will have a neutron flux of 1.99
:math:`\text{neutrons / s / cm}^2`.

As a special case, estimating the neutron flux from ambient backgrounds is very challenging.
Instead, specify the neutron intensity as a multiplicative factor relative to the
measurements used in the base spectra that describe the ambient background. For example, an ambient
background base spectrum is measured to be 5 neutrons / minute. In the base spectrum, this is
recorded as ``<neutron_Sensitivity>`` 5/60 =0.0833. If you create a scenario that
includes this background, set the ambient background neutron intensity to 1. If you want to simulate
twice as much background, set neutron intensity to 2; RASE will simulate a background with an expectation
of 10 neutrons / minute.

*****************************
 Output neutrons to template
*****************************

After simulating neutrons in RASE, you will often want to record results in the format expected by
a specific replay tool. The approach in :ref:`n42_templates` can be augmented by adding
additional fields to the template:

.. code::

   ${neutrons}
   ${secondary_spectrum.neutrons}

These two fields will be filled with the neutron results from the foreground simulation and
secondary background simulation, respectively.

Below is a simple example of a template containing neutrons. Adapt this example to the
expectations of the replay tool you intend to use:

.. code::

   <RadMeasurement id="Foreground">
       <MeasurementClassCode>Foreground</MeasurementClassCode>
       <RealTimeDuration>PT${scenario.acq_time}S</RealTimeDuration>
       <Spectrum>
         <LiveTimeDuration Unit="sec">PT${scenario.acq_time}S</LiveTimeDuration>
         <ChannelData> ${sample_counts} </ChannelData>
       </Spectrum>
       <GrossCounts id="neutrons">
         <CountData> ${neutrons} </CountData>
       </GrossCounts>
   </RadMeasurement>
