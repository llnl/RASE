.. _dynamic_output:

##################################
Interpreting dynamic RASE output
##################################

Each test in the Dynamic RASE YAML configuration produces output according to the
``operations`` block. The output appears on the console and can also be
saved as a CSV table if the configuration includes a ``csv_output`` field specifying a file
path.

The output table always includes columns for each test's name, sources, and replications.

If the ``evaluate_detection`` operation is enabled (it generally requires the ``output_files``,
``replay_files``, ``translate_replay``, and ``evaluate_detection`` in the same or previous configurations) a column labelled
"Prob. of
Detection" will be output. It indicates the number of replications in which the replay tool's
output contained a detection of the value specified by the ``replay_name`` parameter in the scenario
for this test.

If the ``print_scores`` operation is enabled, one column is output for each scorer and each source
across all tests (each source gets its own score). The meaning of these scores is specific to
each scorer.

If the ``show_plots`` operation is enabled, plots are displayed according to the ``plots`` block in
the configuration. Use these plots to visualize the behavior of the models trained for the
tests.