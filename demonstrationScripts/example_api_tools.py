###############################################################################
# Copyright (c) 2018-2026 Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
#
# Written by J. Brodsky, J. Chavez, S. Czyz, G. Kosinovsky, V. Mozin,
#            S. Sangiorgio.
#
# RASE-support@llnl.gov.
#
# LLNL-CODE-2014600, LLNL-CODE-829509
#
# All rights reserved.
#
# This file is part of RASE.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED,INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
###############################################################################
"""
A series of example functions that demonstrate how to access RASE tool functions via API calls
"""
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

def example_strip_results():
    """
    Demonstrates how to use the API to strip the nuclide results from all files in a directory.
    This functionality is applicable beyond simply removing isotope ID results in bulk: by changing the
     "removal_tag" argument, one can use this function to strip out any generic xml block
    :return:
    """
    import shutil
    from pathlib import Path
    from src.rase_functions import remove_xmlblock

    # required arguments
    in_dir = Path(__file__).parent / '..' / 'tests' / 'example_remove_results'
    out_dir = Path(__file__).parent  / 'out'

    # optional arguments
    removal_tag = 'AnalysisResults'                 # default, choose the tag of the block you want to remove
    copy_unmodified = True                          # default, copies all files including those without results
    log_noanalysis_files = True                     # default, creates a text file that records which input files had
                                                    #      no analysis results block
    additional_suffixes = ['*.txt', '*.TXT']        # search for files with these suffixes in addition to the default
                                                    #      suffixes (*.n42, *.N42, *.xml, *.XML)

    try:
        shutil.rmtree(out_dir)
    except FileNotFoundError:
        pass

    # execute the function
    n_converted, n_copied = remove_xmlblock(in_dir, out_dir, removal_tag=removal_tag, copy_unmodified=copy_unmodified,
                    log_noanalysis_files=log_noanalysis_files, additional_suffixes=additional_suffixes)
    # print the output
    print(f'Conversion complete: converted {n_converted} files, copied {n_copied} unconverted files')


if __name__ == '__main__':
    example_strip_results()