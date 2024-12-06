rem This script must be placed and executed from the same folder as the DetXAnalysisEngineOffLineTool executable

@echo off
setlocal enabledelayedexpansion

rem Change the current directory to the directory where the script resides
rem This is required because DetXAnalysisEngineOffLineTool requires it
cd /d "%~dp0"

rem Check if both input_dir and output_dir paths are provided as arguments
if "%~1" == "" (
    echo Please provide the input directory path as the first argument.
    goto :eof
)
if "%~2" == "" (
    echo Please provide the output directory path as the second argument.
    goto :eof
)
set "input_dir=%~1"
set "output_dir=%~2"

rem Get the parent folder of the output directory
for %%I in ("%output_dir%\..") do set "parent_directory=%%~fI"

rem Create an empty text file to store the results in the parent directory of output_dir
set "batch_input_file=%parent_directory%\batch_input.txt"
type nul > "%batch_input_file%"

rem Loop through all files in the input directory
for %%F in ("%input_dir%\*.*") do (
    rem Extract just the filename without the path and change the extension to json
    set "filename=%%~nF.json"
    rem Append the required command line arguments for batch feature of the replay tool
    echo --foreground "%%~fF" --background "%%~fF" --inputType "N42" --outputDirectory "%output_dir%" --outputFileName "!filename!" --backgroundN42ReadAs "background"  >> "%batch_input_file%"
)

DetXAnalysisEngineOffLineTool --batch "%batch_input_file%"

endlocal
