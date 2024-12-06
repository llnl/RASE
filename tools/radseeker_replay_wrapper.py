
"""
This script automates the process of running RadSeeker's GUI-only replay tool (Smith's HPRID Batch Analysis software) 
Usage:
    radseeker_replay_wrapper.py <input_dir> <out_dir> [--batch_analysis_path <path_to_BatchAnalysis.exe>]
Arguments:
    input_dir (str): Path to the input directory containing the files to be analyzed.
    out_dir (str): Path to the output directory where the results will be saved.
    --type (str, optional): Type of detector (NaI or LaBr). Defaults to 'NaI'.
    --batch_analysis_path (str, optional): Path to the BatchAnalysis.exe. Defaults to 
        "C:\\Program Files (x86)\\Smiths Detection\\HPRID Batch Analysis\\BatchAnalysis.exe".
Notes:
- The script uses pywinauto to interact with the GUI elements of the Batch Analysis software.
- The script is somewhat fragile as it relies on keyboard shortcuts to interact with the software. It will fail if the app loses focus.
"""
from pywinauto import Application
from pywinauto.keyboard import send_keys
from pathlib import Path
import os
import argparse

parser = argparse.ArgumentParser(description="Replay automation for Smith's HPRID Batch Analysis")
parser.add_argument('input_dir', type=str, help='Path to the input directory containing the files to be analyzed')
parser.add_argument('out_dir', type=str, help='Path to the output directory where the results will be saved')
parser.add_argument('--type', choices=['NaI', 'LaBr'], default='NaI', help='Type of detector (NaI or LaBr)')
parser.add_argument('--batch_analysis_path', type=str,
                    default="C:\\Program Files (x86)\\Smiths Detection\\HPRID Batch Analysis\\BatchAnalysis.exe", 
                    help='Path to the BatchAnalysis.exe')
args = parser.parse_args()

input_dir = Path(args.input_dir)
out_dir = Path(args.out_dir)

# check user input arguments
if not input_dir.exists():
    raise FileNotFoundError(f"Input directory '{input_dir}' not found.")
if not any(f.name.endswith('_U.n42') for f in input_dir.iterdir() if f.is_file()):
    raise FileNotFoundError(f"No '_U.n42' files found in the input directory.")

app = Application(backend="win32").start(args.batch_analysis_path)

main_dlg = app.window(title_re='HPRID')
main_dlg.wait('visible', timeout=5, retry_interval=1)

# jow to lookup the children of a dialog
# main_dlg.dump_tree(depth=2)

# open the batch analysis - I can't find a way to access the menu directly 
send_keys('%FB')

# Set the output directory
os.makedirs(out_dir, exist_ok=True)
main_dlg.window(auto_id='outputDirTextBox').set_text(f'{out_dir}')
main_dlg.window(auto_id='outputDirTextBox').type_keys('{TAB}')  # to trigger the updated text

# Set the analysis type
main_dlg.window(auto_id='analysisType_ComboBox').select('NaI Handheld' if args.type == 'NaI' else 'LaBr Handheld')

# Add files from input folder 
main_dlg.window(best_match='Add Files').click()

open_dlg = app.window(title_re='Open')
open_dlg.wait('visible', timeout=5)
open_dlg.window(best_match='File name:Edit').set_text(f'{input_dir}')
open_dlg.window(best_match='File name:Edit').type_keys('{ENTER}')

# select all files - I can't find a way to access them directly via a control
open_dlg.window(best_match='File name:Edit').type_keys('+{TAB}')
send_keys('^a')

open_dlg.window(best_match='Open', class_name='Button').click()

# wait for the files to be loaded
main_dlg.StartButton.wait('enabled', timeout=300, retry_interval=1)

main_dlg.StartButton.click()

# wait for the analysis to finish
main_dlg.Remove_Selected.wait('enabled', timeout=300, retry_interval=1)

main_dlg.close()
