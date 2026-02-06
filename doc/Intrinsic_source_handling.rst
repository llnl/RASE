.. _intrinsic_source_handling:

##########################################################################
 Working with instruments with an internal (intrinsic) calibration source
##########################################################################

Weak sources located inside the device are sometimes used in radiation detection instruments to
provide continuous calibration of the energy scale and to stabilize against drift from environmental
and electronics factors. The continuous presence of such a source, typically Na22 or Cs137, produces
spectra that always include the source characteristic peaks in proportion with the measurement
dwell time. Therefore, detectors with internal (also called intrinsic) sources require special
handling with RASE.

Treatment of detectors with internal sources depends on whether the internal source spectrum can
be properly subtracted from the background data, as described below.

More robust handling of internal sources is planned for future versions of RASE.

********************************************
 Instruments with separable internal source
********************************************

If the internal source spectrum is known and can be subtracted from all spectra, including the
background, then RASE only requires that the internal spectrum be provided as a secondary so it
can be added to the sample spectra correctly. More specifically:

-  Create RASE base spectra where one of the secondary spectra is the internal source.

-  After adding base spectra to a detector, in the "Type of secondary spectrum" section of the
   detector creation window select "Add secondary (intrinsic activity) to sample spectra" and
   select the appropriate spectrum class code.

-  If the detector requires both an onboard background spectrum and an intrinsic source, either
   select "no secondary spectrum (other than intrinsic)" and adjust the template to explicitly
   include the background spectrum of interest (in which case RASE will provide the intrinsic
   spectrum as the secondary spectrum), or ensure the template is configured to record the
   appropriate class codes as specified in the detector creation screen.

-  Proceed with the RASE workflow as usual. Sample spectra will include the intrinsic source
   spectrum properly adjusted for the scenario dwell time.

**********************************************
 Instruments with inseparable internal source
**********************************************

For certain instruments, the internal source cannot be properly subtracted from the background
spectrum without introducing noticeable artifacts. Handling this situation is more complex:

-  Create RASE base spectra as usual, leaving the background with the internal source included.
   Subtraction of background plus internal source is usually possible for all other sources and is
   therefore handled normally. Add the background with the internal source as the secondary spectrum
   in the base spectra.

-  When adding base spectra to a detector, flag with the provided checkbox any spectrum that
   contains an internal source. Upon import, base spectra flagged this way will have the label
   "wIntrinsic" added to their material name.

-  Spectra flagged to include an inseparable internal source spectrum cannot be scaled by dose (or
   flux). If included in the scenario, they will only be scaled by the dwell time, and RASE will
   automatically fix the dose (or flux) value. No more than one material with an intrinsic source is
   allowed per scenario.

-  Do not select "Add secondary (intrinsic activity) to sample spectra" in the "Type of secondary
   spectrum" section of the detector creation window. The internal source contribution will be
   accounted for via its inclusion in a base spectrum file.

The intrinsic source is an essential component of the spectrum. Ensure that the background with the
internal source present is included in the definition of any scenario you run with that detector.