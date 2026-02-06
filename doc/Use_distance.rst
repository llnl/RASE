.. _use_distance:

#################################
Use source-to-detector distance
#################################

Sometimes it's more convenient to work in units of distance between the source and the detector
rather than in units of source dose or flux. This is especially useful when you are
comparing RASE predictions to data collected with a source of known intensity at specific
distances.

Converting dose to distance is trivial by scaling for :math:`1/d^2` if the
dose or flux is known at a single distance for the source of interest. To make this easier, RASE
provides the ability to apply this :math:`1/d^2` scaling in the Create Scenario Range dialog and
when plotting results by selecting the `distance` label for an axis.

You can obtain the required dose or flux at a fixed distance either by direct measurement or
by modeling. Among others, modeling tools like GADRAS and `InterSpec
<https://sandialabs.github.io/InterSpec/>`_ offer this capability.