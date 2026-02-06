.. _dynamic_requirements:

###############################
 Requirements and installation
###############################

****************************
 Distribution and operation
****************************

Dynamic RASE is written in Python and is open source. The source code is available on the
"dynamic" branch of the repository at https://github.com/LLNL/RASE.

Although it borrows heavily from Static RASE, the current v1.0 release is not natively
integrated into the RASE GUI and does not seamlessly join the Static RASE workflow. This means
you can use Dynamic RASE independently of Static RASE while it remains aligned in approach and
methodology. The Dynamic RASE GitHub branch contains only the files needed to build and
run Dynamic RASE.

Like Static RASE, Dynamic RASE is intended to be compatible with all mainstream platforms and
operating systems. The binary is currently distributed as a Windows executable, but because it is
coded in Python it can be compiled from source to run on macOS and Linux operating systems. The
Windows binary executable has been tested in Windows 10, and can be run without any additional
downloads or permissions. Instructions for compilation can be found on the GitHub distribution page
in the "compilation_instructions.txt" file.

**************
 Requirements
**************

To use all functions of Dynamic RASE, you must have access to the following additional files and utilities:

-  **Base spectra** for the instruments under evaluation. Base spectra must be in the
   \*.n42 format and should meet the Dynamic RASE standard requirements. See
   :ref:`dynamic_create_base_spectra`. The current library of dynamic base spectra is not included
   with the Dynamic RASE distribution and must be requested separately. However, a set of example
   dynamic base spectra is provided with the distributable
   for workflow testing and demonstration.

-  **Replay tools** which are stand-alone programs that replicate the radioisotope identification
   software deployed on the instrument. These are generally provided by the manufacturer, and can be
   executed from the command line or have a native graphical user interface.
   A demo replay tool is provided with the RASE distribution
   for testing purposes.

-  **Instrument-specific n42 templates** used by RASE to generate sample spectra in the
   native format required by the vendor replay tool. See :ref:`dynamic_n42_templates` for details on
   creating a template for a new dynamic instrument; instructions for creating templates for
   static systems are in the Static RASE manual. Templates for some compatible instruments
   are provided with the RASE distribution.

-  **Results translators**: executable programs that convert replay tool outputs into a format
   compatible with RASE. If the replay tool already outputs RASE format, a results translator
   is not required. Translators for some instruments are already developed and are
   included with the RASE distribution. If you need a translator for a specific instrument or
   replay tool, please contact the RASE developers. Details on the format of the identification
   results files are provided in :ref:`dynamic_output`.

**********************************
 Installation and getting started
**********************************

-  Create a dedicated directory for Dynamic RASE and extract the Dynamic RASE archive there,
   which contains the executable and important subdirectories. By default, Dynamic RASE uses paths
   relative to the location of the Dynamic RASE executable. Keep the archive structure as it appears
   when first extracted.

-  Make sure that the extracted archive contained the executable and the following files and
   subdirectories (names are arbitrary) with the appropriate contents:

      -  several .yaml files (see :ref:`dynamic_operation` for details on these files);

      -  subdirectory for base spectra;
            -  subdirectory for replay tools;
            -  subdirectory for translators.

-  Dynamic RASE stores its database in a sqlite file inside the Dynamic RASE data directory. This
   file should not be deleted or modified by the user.

-  Output from Dynamic RASE is placed in a "tests" directory created in the working directory. This
   folder is created at runtime.