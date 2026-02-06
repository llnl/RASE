.. _dynamic_mechanics:

###########################
 Mechanics of Dynamic RASE
###########################

Dynamic RASE uses the same downsampling method as Static RASE, but along a path: instead of
sampling from a single fixed base spectrum for an entire simulation, the sampled base spectrum
varies depending on where in space the detector is. The base spectrum at each point is
determined by a detector response map, interpolated and extrapolated across space using a
"Gaussian process". The response map is built from a set of user-provided long-dwell static base
spectra, or "training points", collected by placing the source at several locations about the
detector. Dynamic RASE creates a unique interpolation for each energy bin, allowing for
effects of environmental conditions, such as shielding, to be adjusted with
respect to position. The base spectra are scaled by live time, so a set of spectra can consist of
measurements with many live times (often necessary to achieve reliable and representative counting
statistics, particularly in instances with shielding or with wide angle/distant sources).

.. figure:: _static/dynamic_training_points.png
   :scale: 80 %

   **One example of where to take several long-dwell measurements (training points) to generate the detector
   response map**

******************
 Gaussian process
******************

Dynamic RASE uses a Gaussian process model for interpolation. This model determines
the relationship between data points via a "kernel", which makes nearby points strongly
correlated and distant points uncorrelated. In the context of Dynamic RASE, the data points passed to the
kernel are the counts in the
base spectra supplied by the user. The Gaussian process uses the kernel relationships to generate
many smooth functions that run through the data. These functions converge to a single "best fit" curve that
becomes the 3D detector response map.
Dynamic RASE builds a separate Gaussian process model for each energy bin, so if the base
spectra have 1024 bins, there will be 1024 models.

The kernel in Dynamic RASE is a compound kernel with angular and radial components that
compute correlations in spherical coordinates. Assuming the detector face is
located at (x, y, z) = (0, 0, 0), data from
(30, 30, 0) and (150, 150, 0) have the same angular position
but very different radial distances. Conversely, (-50, 50, 0) and (50, 50,
0) share the same radial distance but differ in angle.

If you can make realistic assumptions about the data before fitting it to
the Gaussian process, you can improve fit success. For radiation sources, a common
assumption is isotropic emission and
intensity that follows 1/r^2. The Gaussian process fits data after transforming it to account for
the expected 1/r^2 behavior. The response map is normalized by
the regression coefficient to center it at zero. A response map from measurements that
perfectly follow 1/r^2 would be flat and equal 0 everywhere. Therefore, without
additional data, the Gaussian process will trend back to 0 (i.e., only 1/r^2
effects). Regions or training points with lower-than-expected counts (e.g., due to
geometric effects or shielding) appear negative, and regions with higher counts appear positive.
Unless the response perfectly matches 1/r^2 (in which case every value would be 0), each map
should include at least one negative and one positive point.

The Gaussian process places no "quality" restrictions on supplied spectra and accounts for counting
statistics when fitting. If you provide a spectrum with good
counting statistics, the Gaussian process will weight that point highly and is therefore more
likely to pass through, or very near, that point. If a spectrum has poor counting statistics, the
Gaussian process still uses it in the fit but assigns it little weight. Because of this weighting
adding more data, even with poor counting statistics, is unlikely to harm the fit significantly.
In light of this, you will often benefit from providing several measurements with modest collection
times instead of a small number of measurements over longer times.

The Gaussian process infers a "length scale" for the radial kernel and an analogous parameter for the
angular kernel. These parameters describe the distance at which two points are considered
"close" and therefore highly correlated in the model. The Gaussian process software will fit these
length scales from the input data. Thus, data that shows large changes in intensity over small
changes in radius or angle will make the Gaussian process infer a short length scale. In cases
with short-distance variations (for example, shielding with sharp edges), the model will require
more finely spaced input data to achieve good accuracy than scenarios where the detection behavior
is smooth over longer distances.

The current release of Dynamic RASE provides a single kernel.
Additional kernels are in development.
These new kernels will let users impose explicit assumptions on the model.
Users interested in these features should contact the developers.

***********************
 Sampling along a path
***********************

Defining a scenario in Dynamic RASE requires that the user supply a list of sources involved in the
scenario (and their respective intensities), the detector under test, and a path that the
source(s) travel relative to the detector. To define a path, set a starting point (in 3D space), an
ending point, and a travel time. The user also specifies the "output period", which indicates how often an
integrated sample spectrum is created, and a "sample frequency", which indicates how many
sub-samples make up a period. Depending on how the user defines the output
period, Dynamic RASE will either create one spectrum, which is the total spectrum observed by the
detector as the source travels along the full path, or several spectra in a time series, each
representing the spectrum acquired during an output time period.

To create an accurate simulation, the user-defined path is broken up into many uniformly distributed
positions, or "sample points", in 3D space, as specified by the user-provided sample frequency. Note
that you should ensure there are enough points to capture any significant fluctuations in the
detector response along the path. At each sample point the response map for one of the sources in
the scenario is queried at every energy bin to determine the expected counts in that bin if the
source were located at that position. The queried spectrum is then scaled by the "dwell time",
calculated as the total travel time divided by the total number of sample points. The spectrum,
bin-by-bin, is converted to a sample spectrum by randomly sampling from the Poisson distribution,
where :math:`\lambda` is equal to the counts in that bin that are expected to be
observed during the dwell time, and then scaled to the appropriate source strength as set by the
user in the scenario definition. This is repeated for every source defined in the scenario, with the
new source sample spectrum being added to that of the previous source(s). The resulting sample
spectrum at each point is summed with other sample spectra across each user-defined output period to
give a representation of what the detector would have seen from the source as it traveled across it.
This entire process is repeated for however many replications you specify.

.. figure:: _static/dynamic_path.png
   :scale: 40 %

   **An example of how sample spectra are created in Dynamic RASE. In this particular example, there is only
   one output period, which is equal to the total length of the path. The static spectra shown in the bottom
   left are illustrative of what would be queried at each sample point.**

.. _mechanics_proxy_sources:

***************
 Proxy sources
***************

Though a perfect dataset would include long-dwell measurements on a grid with centimeter
granularity, Dynamic RASE is designed to maximize simulation capability while minimizing
experimental load. Proxy sources reduce the number of base spectra needed to simulate sources.

The proxy source approach assumes each energy bin is independent of neighboring bins. Under this
assumption, the relative detector response between locations is the same for a given energy bin
regardless of the overall spectrum shape. Proxying uses a detector response map generated for one
source (the "proxy" source) and applies it to a spectrum from a different "target" source. Because
the response map at each energy represents the relative fluctuation across space, applying it to the
target simply scales the fluctuations relative to the target's anchor spectrum. For example, a
detector response map generated for Cs137 using several training points could be applied to a single
measurement of WGPu to approximate the response map that would result from multiple WGPu training
points.

Ideally create proxy detector response maps using sources with reliably high counting statistics in the
bins of interest (e.g., you would not use Cs137 as a proxy for Co60 because Cs137 yields 0 counts
at the photopeak energies of Co60).