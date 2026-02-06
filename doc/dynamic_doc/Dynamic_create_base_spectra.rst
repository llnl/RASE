.. _dynamic_create_base_spectra:

##############################
 Base spectra in Dynamic RASE
##############################

To simulate the detector response to a source in Dynamic RASE, a detector response map must be built
for that source. This map is constructed from measured spectra, or "base spectra", recorded at
multiple locations. These base spectra encode the information needed for simulation, such as a
gamma spectrum, calibration coefficients, real and live measurement times, source location relative
to the center of the detector face, and the "quantity" of the source.

To create base spectra for Dynamic RASE, do the following:

#. Acquire a set of source and background measurements at multiple locations
#. Process the measured spectra to separate the source from the background
#. Produce a properly formatted n42 file for ingestion into RASE

Dynamic RASE is released with several sets of example dynamic base spectra. These spectra were
simulated using GADRAS for a non-specific instrument. They are in the `dynamicBaseSpectra`
directory.

For additional details about base spectra, refer to :cite:`RASE_standard`

************************************************
 General considerations for spectra acquisition
************************************************

Each source to be simulated in a dynamic scenario must have a detector response map associated with
it. This map is built over space by interpolating and extrapolating from spectra recorded at many
locations. The more spectra you acquire, and the more widely distributed they are across the space
of interest, the more accurate the response map will be. Because the map accounts for counting
uncertainty when creating a universal fit, higher total counts in each spectrum yield a more
precise detector response map.

With these points in mind, you can acquire base spectra in three ways to generate a good detector
response map:

#. Acquire high-statistics static spectra at various locations. Place the detector and source in a
   fixed geometry, measure for a long time, record the spectrum, and repeat at many locations. This
   approach is recommended for high precision, especially if the points match the paths you plan to
   simulate (for example: measuring points at and around the standoff where you expect source
   pass-bys).

#. Acquire short-dwell static spectra at many locations. Use this when building large detector
   response maps where long dwell times at every point are impractical.

#. Conduct a dynamic measurement where the source and detector move relative to each other, and
   create many integrated short spectra from that measurement. Assign each integrated short spectrum
   a location along the path. This is ideal if you have a programmable track so the source can move
   slowly past the detector for a long period. It reduces experimental effort while producing many
   spectra.

Complete this procedure for each source of interest. If you plan to use proxy sources (see
:ref:`mechanics_proxy_sources` for details), you may only need to do the full procedure for a few sources. In the
proxy case, you can apply detector response maps created for those sources as scaling maps to a
single high-statistics anchor spectrum from a different source. For example, if you create a full
detector response map for Cs137, you might record one WGPu spectrum at a known location and use the
Cs137 map relationships to scale the WGPu spectrum over space. Where possible, use a proxy map from
a source whose photopeaks are near the photopeaks of the source of interest.

Note that Dynamic RASE imposes no strict requirements on the number or quality of spectra you
provide. It will accept a small set with poor counting statistics or a large set of high-statistics
spectra. Thus, options 1 and 2 above are the same procedure, differing only in the number of spectra
and acquisition time per spectrum. Base spectra do not need to be acquired at the same locations for
different sources: each source gets its own detector response map defined over all space. Base
spectra used to define a map may have different live times or source intensities: each base spectrum
records its own live time and "quantity". This lets you build a response map for a single isotope
using multiple sources. For instance, to build a Cs137 response map you could use a low-activity
source up close (to avoid pileup) and a high-activity source far away (to reduce needed dwell time).

Dynamic RASE assumes the background spectra you provide are spatially uniform. There is no background
map; you need only one background measurement for a given detector.

Each base spectrum file must record the detector calibration coefficients at the time of
measurement. The calibration coefficients for all base spectra associated with a detector, regardless
of source, must be the same. Each file must also record the real and live time of the measurement
and the source location relative to the center of the detector face in (x, y, z). For Dynamic RASE,
x is the horizontal offset from the center of the detector face, y is the standoff, and z is the
vertical offset. Finally, each file must record the "quantity" of the source and its units. Dynamic
RASE currently supports source quantities that do not change with relative source-detector position,
such as activity ("uCi") or mass ("kg"). The exception is background: its quantity is expressed as
dose in units of "uSv_h". Units must be consistent across all base spectra used to build a single
detector response map, but different sources can use different units (this also applies to proxy
sources). For example: you could make a Cs137 response map with units of "uCi" and a WGPu response
map with units of "kg". Each Cs137 base spectrum would note the activity used, and each WGPu base
spectrum would note the mass used. When defining a scenario containing Cs137 and WGPu, the Cs137
quantity is in "uCi" and the WGPu quantity in "kg". Note that Dynamic RASE does not account for
self-shielding effects that might occur with increasing SNM mass; exercise caution when interpreting
results where sample masses differ significantly from base spectrum masses.

*******************************************
 Specific guidance for spectra acquisition
*******************************************

A measurement should normally be performed in well-controlled laboratory conditions with one or more
radioactive sources. Follow these recommendations to obtain high-quality base spectra:

-  The measurement scenario (source strength, shielding) should ensure a significant fraction of
   the instrument count rate arises from the source. If noting dose rate, the source dose should be
   at least five times above background. If measuring source flux, the net counts in the photopeak
   of interest should be at least 350-550. This may not be possible when the source is far from the
   detector.

-  For long-dwell high-statistics spectra, measure long enough that the photopeaks of interest have
   at least 10,000 counts each. This recommendation is less critical if you supply many base spectra
   or if base spectra are close together.

-  Verify that pile-up and dead time are insignificant. Aim for dead time no more than 2%.

-  If possible, keep the detector fixed and move the source as needed. Do not rotate the detector
   during or between measurements to properly capture angular effects.

-  Use an instrument orientation relative to the source that reflects intended field usage.

-  Adjust acquisition times so the total counts in any base spectrum are at least ten times the
   total counts expected in a scenario segment nearer to that base spectrum than any other. Calculate
   this using the formula: :math:`Q_0 \cdot T_0 > 10 \cdot Q_s \cdot {T_{sseg}}`, where :math:`Q_0` is the quantity in the base spectrum,
   :math:`T_0` is the base spectrum live time, :math:`Q_s` is the scenario source quantity, and
   :math:`{T_{sseg}}` is the total time the scenario path is closer to that base spectrum than any other
   (i.e., the time spent on that path segment). For proxy sources, apply the same approach but
   replace each surrogate point with a properly scaled version of the anchor point.

-  If creating base spectra on a continuously moving track, ensure track velocity times source
   activity is at least ten times that of the scenario on the same track. Use :math:`Q_0 \cdot V_0 > 10
   \cdot Q_s \cdot V_s`, where :math:`Q_0` is the base-spectrum quantity, :math:`V_0` is the track
   velocity, :math:`Q_s` is the scenario quantity, and :math:`V_s` is the scenario velocity.

Acquire a high-statistics long-dwell (at least 1 hour) background spectrum under the same experimental
conditions as the source measurements.

Record the activity or mass of the source used for each base spectrum.

If you cannot obtain measured spectra, you may use simulated spectra with RASE.

**************************************************
 Recommended spatial distribution of base spectra
**************************************************

The detector response map will better represent reality near base spectra and will better capture
spatial trends as you provide more data. Thus, more base spectra are beneficial. In limited data
situations, follow these recommendations to create smooth and accurate detector response maps. Dynamic
RASE can enforce symmetry; if you simulate a symmetric space, you need not take points on both sides
of the detector centerline. The following recommendations assume high counting statistics, enforced
symmetry, and simulation of several path types: fixed-standoff passby, diagonal pass, straight-on
approach/retreat, etc. They also assume you measure and simulate in a plane at the detector height
(vertical standoff = 0).

-  In unshielded symmetric conditions, simulations using GADRAS-based spectra indicate a smooth map
   can be generated from as few as four points. However, acquire more points to avoid degeneracies,
   particularly in low-count energy bins. Seven well-distributed points are generally sufficient for
   smooth maps.

-  Take at least two, preferably three, measurements directly in front of the detector at different
   distances to capture standoff dependence.

-  Aside from head-on measurements, avoid more than two measurements at any fixed radius or angle,
   as this can produce degeneracies and artifacts.

-  Place measurements beyond the extremes of any expected simulated path in all directions.

For more specific cases, follow these additional recommendations:

-  If you will simulate only a specific path (e.g.: a passby from :math:`x_1` to :math:`x_2` at a
   particular standoff), focus base spectra acquisition along that path for the most accurate
   results.

-  If you supply many low-statistics measurements instead of a few high-statistics ones, ensure the
   total counts meet the recommendations above. For example, 14 measurements with 5,000 net photopeak
   counts each roughly replace seven measurements with 10,000 counts each.

-  If simulating sharp transitions, take a denser set of measurements around the transition. For
   example, when simulating the edge of a shield, take at least one measurement on each side of the
   shield at multiple distances.

**************************
 Process measured spectra
**************************

To support varying scenarios with different sources and dose rates, RASE requires spectra that
represent the instrument response solely to the source. Remove background and any spurious components
(e.g., intrinsic calibration source) from collected base spectra.

Obtain the background-subtracted spectrum by subtracting, channel-by-channel, the normalized
background spectrum from the normalized source spectrum (normalize both by live time). Re-bin if
needed to account for gain shifts between source and background. If an intrinsic calibration source
appears in the measured source spectrum, subtract it as well. When generating base spectra of natural
radiation background, do not perform background subtraction.

.. _dynamic_base_spectra_naming_convention:

****************************************
 Dynamic base spectra naming convention
****************************************

The file name for the base spectra follows the format ``Vvvvv_Mmmm_Source_Description.n42`` consists
of four fields (vendor’s abbreviation, instrument model abbreviation, source name and scenario
description) each separated by an underscore character:

-  Vvvvv = a four-character manufacturer abbreviation
-  Mmmm = a three-character alphanumeric model number abbreviation
-  Source = a label describing the source
-  Description = a label describing the shielding scenario or other relevant measurement conditions,
   such as position and quantity
-  Other = a label that distinguishes between files based on source strength, location, etc.

The source description label shall follow a defined naming convention:

.. table::
   :widths: 550 290 910

   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | **Nuclide or aggregate**              | **Source label**            | **Comments**                                                                                                                                                                                                                                                        |
   +=======================================+=============================+=====================================================================================================================================================================================================================================================================+
   | 235U                                  | HEU                         | Highly enriched uranium with 235U/U above or equal to 20%                                                                                                                                                                                                           |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 235U+238U                             | LEU                         | Low enriched uranium with 235U/U between 0.7% and 20%                                                                                                                                                                                                               |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 238U                                  | DU                          | Depleted uranium with 235U/U below 0.7%                                                                                                                                                                                                                             |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 239Pu+240Pu+241Pu                     | WGPu                        | Weapons grade plutonium with 239Pu/Pu above or equal to 93%                                                                                                                                                                                                         |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 239Pu+240Pu+241Pu                     | RGPu                        | Reactor grade plutonium with 239Pu/Pu below 93%                                                                                                                                                                                                                     |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 40K                                   | Knorm                       | Potassium fertilizer or Potassium salt                                                                                                                                                                                                                              |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 238U decay chain                      | Unorm                       | Uranium decay chain in equilibrium with daughters (e.g. a base spectrum of phosphate fertilizer)                                                                                                                                                                    |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | 232Th decay chain                     | Tnorm                       | Thorium decay chain in equilibrium with daughters (e.g. a base spectrum of welding rods, camera lenses or lantern mantles)                                                                                                                                          |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Natural radiation background          | Bgnd                        | Contribution from non-naturally occurring radioactive material into the spectrum shall be negligible                                                                                                                                                                |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | nnnMM                                 | MMnnn                       | All other nuclides, MM is a 2-alphabetic placeholder for the nuclide name according to *ISO 80000-9:2009, Quantities and units – Part 9: Physical chemistry and molecular physics* and nnn is an up to 3-digits placeholder for nuclide atomic number, e.g. Cf252   |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   | Other nuclides mixture                | Name1+Name2                 | Separate each source name with a ‘+’ sign. Individual names are based on the rules above                                                                                                                                                                            |
   +---------------------------------------+-----------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

For example, the name ``Vabcd_M123_Am241.n42`` would represent the spectrum of a Am241 source for
instrument ‘123’ manufactured by ‘abcd’. Similarly, ``Vabcd_M123_Cs137_12mmSteel.n42`` would
represent the spectrum of a Cs137 source shielded behind 12 mm of steel.
``Vabcd_M123_Ba133_{100uCi}{dx=-250}{dy=150}{dz=0}`` would represent a Ba133 source at 100
:math:`{\mu}`\ Ci located at position x = -250, y = 150, and z = 0.

*******************************
 Format n42 base spectrum file
*******************************

The format of the base spectra is based on the ANSI N42.42 format.

The ``<N42InstrumentData>`` element is the parent element for all data in the file. It must contain
one ``<Measurement>`` element, representing a measurement. The ``<Measurement>`` element contains
various child elements that describe the instrument and the data collected.

Notes:

-  The element ``<Position Units="___">`` describes the location of the source in relation to the
   center of the detector face. The user may define arbitrary units for the position. The <x>, <y>,
   and <z> subelements are all in the same units as specified by the user in the position tag.

-  The element ``<Quantity Units="___">`` describes the intensity or amount of the source, depending
   on the units specified by the user. Background units should be specified in dose, with
   Units="uSv_h". Sources should be specified with values that do not change based on position, such
   as activity ("uCi") or mass ("kg"). All base spectra used to build a single detector response map
   for a source must have the same units, but each spectrum can have different quantities.

-  All base spectra for a given instrument including background must have the same <calibration>
   element, i.e. be defined in the same energy scale.

-  If required by the identification algorithm, a secondary spectrum (e.g. a background spectrum or
   the spectrum of the internal calibration source) can be provided after the measurement spectrum
   as an additional ``<spectrum></spectrum>`` element.

-  For additional details, refer to IEC Standard, *Radiation instrumentation – semi-empirical method
   for performance evaluation of detection and radionuclide identification*, 2016

The following example of the XML data file is from a 1024-channel MCA. The indented formatting is
purely for readability and is not required. Line breaks are not required, and there is no limit to
line length. Spectrum compression according to the ANSI N42.42 is allowed.

.. code:: XML

   <?xml version="1.0" ?>
   <N42InstrumentData>
     <Measurement>
       <Spectrum>
         <RealTime Unit="sec">PT1800.0S</RealTime>
         <LiveTime Unit="sec">PT1797.3070068359375S</LiveTime>
         <Calibration Type="energy" EnergyUnits="keV">
           <Equation Model="Polynomial">
             <Coefficients>0  2.83783197265625  0.0</Coefficients>
           </Equation>
         </Calibration>
         <ChannelData>0 0 1560 5141 5228 5096 5412 5694 6685 11419 45485 110351
         97985 47801 22268 8826 6145 7343 10605 14652 16109 12933 10873 13076
         17162 20769 23530 29227 46107 73393 93887 89434 59289 28738 11569 5858
         4486 4369 4479 4534 4619 4690 4830 4694 4766 4691 4862 4888 5284 5102
         5482 5646 5963 6480 6989 7469 8151 8916 9826 10011 10477 10398 10440
         10170 9954 9653 9526 9212 8994 8675 8078 7712 7548 6895 6467 6120 6078
         6117 5862 5955 5580 5682 5686 5414 5192 4851 4790 4615 4659 4708 4581
         4857 5023 5300 6225 7177 8216 9755 10896 11776 12579 13142 13525 13928
         14760 16180 17801 19036 20401 20702 20675 18828 16807 14324 11730 9431
         8189 7360 8030 9806 12809 16990 22334 28555 35163 41337 46127 49192
         49921 48783 45073 39966 34241 28240 23061 18318 14706 11792 9620 7959
         6297 5366 4199 3429 2421 1794 1201 870 485 270 187 140 22 99 63 49 61
         0 24 7 0 11 35 30 0 29 22 39 62 7 23 46 0 0 0 0 0 0 0 122 16 0 0 0 0 0
         154 0 0 0 0 65 0 4 22 32 31 0 13 10 0 37 0 25 39 0 43 9 25 3 20 24 0 19
         28 19 2 25 0 24 0 38 39 0 30 26 18 3 8 28 0 8 1 15 0 13 38 14 0 0 108
         47 31 28 40 0 15 53 10 4 2 0 44 3 34 47 11 13 7 0 24 34 29 10 7 0 7 0
         41 21 19 17 0 0 2 0 0 0 0 6 0 0 0 0 22 0 0 0 0 8 17 0 34 0 11 8 0 5 31
         0 0 4 30 18 1 0 35 21 8 0 17 8 51 0 0 0 26 19 7 15 44 0 0 6 0 11 0 0 9
         14 0 24 0 7 0 0 31 0 7 33 7 14 0 0 0 11 0 1 27 0 0 0 0 0 0 9 0 2 0 0 33
         0 0 0 13 5 0 4 8 0 6 14 0 0 0 0 19 0 0 28 2 0 0 0 17 0 10 26 0 0 0 18 0
         10 2 6 0 0 0 0 0 0 0 21 0 0 0 1 13 12 0 0 0 5 11 0 0 0 11 0 4 37 40 0 0
         0 34 20 0 33 0 0 0 0 0 0 0 20 0 7 0 0 0 0 19 33 0 0 0 16 31 0 31 21 10
         0 27 0 0 26 0 14 0 0 0 26 26 15 0 0 21 0 4 0 0 0 0 0 0 19 0 0 0 28 1 3
         0 2 13 0 3 0 0 14 0 2 3 0 6 0 0 0 15 0 21 0 0 0 0 9 0 27 32 0 0 5 11 0
         0 0 35 28 0 6 11 2 0 4 0 0 0 0 45 0 0 7 13 13 0 0 0 16 21 0 32 0 15 25
         6 10 11 0 1 6 1 0 11 3 0 0 4 0 2 22 0 0 8 0 8 0 8 0 0 0 0 6 1 0 0 0 4
         0 0 13 2 0 8 12 0 0 8 0 3 0 0 0 0 1 0 5 0 0 0 0 0 0 0 13 0 0 0 0 0 9 0
         0 0 0 13 12 0 64 0 18 0 0 6 11 14 5 0 7 16 0 5 2 0 14 18 0 3 2 11 0 0
         0 7 0 0 4 1 0 12 4 0 8 0 1 3 5 0 0 0 0 0 0 3 5 0 0 0 7 0 0 0 1 3 3 4 1
         9 1 0 4 0 0 0 0 0 0 1 4 0 0 0 0 6 0 0 0 1 4 0 0 0 2 4 0 5 0 1 0 0 4 3 0
         2 3 0 2 1 0 0 3 0 0 7 0 5 0 0 5 5 0 0 0 5 0 0 1 0 1 0 2 0 1 0 0 3 0 0 0
         4 0 0 5 6 0 1 6 2 5 0 0 4 1 0 2 2 4 0 2 0 0 3 6 0 0 7 2 0 0 0 1 0 0 1 0
         0 0 0 0 3 3 0 2 0 5 0 0 0 0 1 1 2 0 0 6 4 0 2 0 0 0 0 0 0 2 0 0 2 0 1 0
         1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2 0 4 0 0 0 2 0 2 1 0 0 0 0 0 0 0 0
         0 2 0 2 0 3 0 2 3 0 0 0 0 0 0 0 0 0 0 2 0 8 8 3 0 0 0 8 5 0 6 0 0 0 0 0
         3 4 0 0 0 0 8 0 2 4 0 6 0 5 2 2 4 8 0 4 0 0 1 4 5 0 0 0 0 3 1 0 0 0 0 1
         0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
         0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
         0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 </ChannelData>
         <Position Units="cm">
           <x>-50</x>
           <y>100</y>
           <z>0</z>
         </Position>
         <Quantity Units="uCi">100</Quantity>
       </Spectrum>
     </Measurement>
   </N42InstrumentData>

.. _dynamic-create_base_spectra: