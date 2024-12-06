.. _neutrons:

*******************
Neutron Simulations
*******************

Capability
==========
RASE is able to ingest base spectra containing neutron data and use that data to simulate neutron detection in scenarios.

RASE can:

1. Load RASE base spectra containing neutron gross count information.
2. Create instruments that include these base spectra
3. Create scenarios that include neutron-emitting sources and ambient background neutrons
4. Simulate combinations of instruments and scenarios, evaluating the expectation value of the gross neutron counts and simulating random fluctuations around that number for each replication
5. Place the simulated neutron results into a manufacturer-specific output format using RASE's template system

RASE cannot:

1. Simulate neutron spectra. RASE only works with neutron gross counts.
2. Predict the neutron emission intensity from a source using its gamma emission intensity (flux or dose). RASE users must know the emitted neutron flux for the scenarios they wish to simulate.
3. Automatically produce neutron-containing base spectra from detector records in a manufacturer-specific format. RASE users must manually add neutrons to base spectra (this feature may be added in a future update).


Creating Base Spectra
=====================
Starting with a RASE base spectra created following the instruction in :ref:`create_base_spectra`, users can add information about the instrument's neutron detection capabilities::


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

1. Add a :code:`<GrossCounts id="neutrons">` block as a child of :code:`<RadMeasurement>`.
2. In this block, include :code:`<neutron_Sensitivity>`, listing the neutron sensitivity factor of this source, calculated as described below.
3. This block may optionally include a :code:`<CountData>` entry. This value is NOT used during any RASE calculations, but may be used as a reminder of the neutron measurement that was used to calculate the neutron sensitivity.

A base spectrum should also contain gamma detection results. For a pure neutron source, the :code:`<RASE_Sensitivity>` should be set to zero. Most neutron emitting sources will produce gammas, and so gamma and neutron information are combined into a single base spectrum file for this source.

Calculating the neutron sensitivity factor
------------------------------------------
The neutron sensitivity factor can be calculated in a similar manner as the gamma sensitivity factor: neutron count rate in the measured spectrum divided by the ground truth neutron flux (in units of neutrons / :math:`\text{cm}^2-s`) at the face of the detector. This is often a difficult quantity to measure empirically, and instead can be calculated using known source activities and determining the solid angle of 1:math:`\text{cm}^2` at that standoff.

.. math::
    S_{\text{neutron}} = \frac{ \text{(net measured neutron counts [n])}/\text{(livetime [s])}}{\text{(neutron flux at measurement location} [\text{n}\text{/cm}^2\text{s}])}

In other words:

.. math::

   S_{\text{neutron}} = \frac{4 \pi \cdot  (\text{source-instrument distance [cm]})^2 \cdot \text{(net measured neutron counts [n])}}{\text{(source activity [n/s])} \cdot \text{(livetime [s])}}

This sensitivity factor has units of :math:`\text{cm}^2`.

NB: the flux calculation is a property of the neutrons emitted by the source and the surface area of the sphere where those neutrons meet the instrument. The face area of the instrument does not enter into this calculation.

In the above example, the sensitivity factor of 0.315 corresponds to 75 neutrons measured from a 1e6 neutrons/s source measured at 2 m for 120 seconds.

Estimating the neutron emission rate for an experimental test source can be challenging. RASE users are encouraged to reference calibration data provided with their sources or calibrate the sources themselves.

As a special case, an ambient background measurement should record the neutron sensitivity factor as if the ground truth neutron flux was 1, as the ground truth neutron flux cannot practically be estimated for an ambient neutron background. In other words:

.. math::
   S_{\text{neutron background}} = \frac{\text{net measured neutron counts [n]}}{\text{livetime [s]}}

A consequence of this decision is that during scenario creation (described below), ambient neutron backgrounds are described in terms of a scaling factor relative to the measurement, e.g. 1x or 2x.

Instrument Creation
===================
Creating a RASE instrument with neutrons only requires providing that instrument with base spectra created as described above. No other changes from the usual procedure are required.


Scenario Creation
=================
When creating a RASE scenario, if any instruments have been created using neutron-containing base spectra, the scenario creation window will contain a column for "Neutron Intensity." When adding a material to a scenario, the user may specify some neutron intensity for that material.

Any material with nonzero neutron intensity in the scenario and nonzero neutron measurement in its base spectrum will cause neutrons to be simulated.

Providing a neutron intensity to a material with no neutrons in its base spectrum will result in zero neutrons in the result. This situation can occur when simulating an instrument without neutron detection capability, which will, as expected, not detect any neutrons in the RASE simulation even in scenarios where neutron-emitting sources are present.

Calculating Neutron Intensity
-----------------------------
The neutron intensity of a material in a scenario is its emitted neutron flux. For example, a source emitting 1e6 neutrons / s observed from 2 m away will have a neutron flux of 1.99 :math:`\text{neutrons / s / cm}^2`.

As a special case, estimating the neutron flux from ambient backgrounds is very challenging. Instead, the neutron intensity should be specified as a multiplicative factor relative to the measurements used in the base spectra describing the ambient background. For example, an ambient background base spectrum is measured to be 5 neutrons / minute. In the base spectrum, this is recorded as :code:`<neutron_Sensitivity>` 5/60 =0.0833. If a user wishes to create a scenario that includes this background, they should set the ambient background neutron intensity to 1. If the user desires to simulate twice as much background, they should set neutron intensity to 2, in which case RASE will simulate a background with an expectation of 10 neutrons / minute.


Output Neutrons to Template
===========================
After simulating neutrons in RASE, many users will want to record results in the format expected by some specific replay tool. The approach in :ref:`n42_templates`  can be augmented by including additional fields in the template::

    ${neutrons}
    ${secondary_spectrum.neutrons}

These two fields will be filled with the neutron results from the foreground simulation and secondary background simulation, respectively.

Below is a simple example of a template containing neutrons. This example must be adapted to the expectations of whatever replay tool the user intends to use::

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

