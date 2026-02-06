.. _troubleshooting:

#################
 Troubleshooting
#################

-  RASE is actively developed and may contain bugs despite extensive testing,
   particularly in the graphical interface and user experience. If you see unexpected
   behavior, report it to the RASE development team at
   rase-support@llnl.gov.

-  If RASE crashes repeatedly, the internal database may be corrupt. The database is a
   .sqlite file stored in the RASE working directory. Delete that file to force RASE to
   create a fresh database at next start. This will erase all user scenario and instrument
   information. The RASE development team may be able to recover data from a corrupt
   database if necessary.

-  If a step after the “Run Replay Tool” step does not return the expected results, the most common
   cause is an incorrectly specified replay tool. In particular, confirm the Command
   Arguments field in the replay tool specification is correct for that tool.

-  RASE creates various log files that can help identify the origin of a crash or unexpected
   behavior.

   -  The main RASE log file ``rase.log`` resides in the same folder as the RASE executable and
      contains traceback information for unhandled exceptions that cause the main code to crash.

   -  The output of the replay tool, if any, is saved in a file called ``replay_tool_output.log``
      located in the sample directory for the specific scenario-instrument being replayed.

   -  In case of errors when executing a results translator, a file called
      ``results_translator_output.log`` is created containing the output log of the translator tool.
      The file is located in the sample directory for the specific scenario-instrument that is
      being worked on.

***********************
 A Note for Developers
***********************

-  If you modify the source code, run the unit test suite periodically. Run the ``test_main.py`` file to
   automatically
   test core RASE functionality. This checks various aspects of the main code. You must have
   ``pytest`` installed on your system to run the suite.