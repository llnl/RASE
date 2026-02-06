.. _import_csv:

##################################
Import scenarios from .csv files
##################################

Scenarios may be directly imported from an .xml file through the :guilabel:`Import` button in the main window.
To import many scenarios, use a .csv file instead.
In a .csv file, each line represents a scenario. The file can contain an arbitrary number of scenarios, but
each scenario may include at most one source and one background material.
The first line must contain the following eight key words, in any order:

   s_fd_mode, s_material, s_intensity, b_fd_mode, b_material, b_intensity, acq_time, replications

This first line should be followed by any number of subsequent lines. Each of these lines should be
filled with the information for the corresponding header column:

   -  s_fd_mode: Source units (DOSE or FLUX)
   -  s_material: Source material
   -  s_intensity: Source intensity, in units of μSv/h or :math:`\gamma/cm^2s`
   -  b_fd_mode: Background units (DOSE or FLUX)
   -  b_material: Background material
   -  b_intensity: Background intensity, in units of μSv/h or :math:`\gamma/cm^2s`
   -  acq_time: Scenario acquisition time
   -  replications: Number of scenario replications

Of these terms, only acq_time and replications are absolutely necessary. If no source (or
background) material is desired, leave the three source (or background) columns blank.

Each scenario line must correspond to a unique scenario.

Upon import, a new scenario group is created and labeled using the name of the imported file.