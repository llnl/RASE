@echo off
setlocal enabledelayedexpansion

REM
REM This script must be placed in and executed from the same folder as the RsiRaseReplay executable
REM

REM Change the current directory to the directory where the script resides
cd /d "%~dp0"

REM Check if both input_dir and output_dir paths are provided as arguments
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

REM Get the parent folder of the output directory
for %%I in ("%output_dir%\..") do set "parent_directory=%%~fI"

REM Generate the AnalysisParams XML file
set "analysis_params=%parent_directory%\AnalysisParams.xml"
(
	echo ^<?xml version="1.0" encoding="UTF-8"?^>
	echo ^<RsiRaseAnalysisParametersDoc^>
	echo     ^<TemplateLibrary^>RASE.tlv3^</TemplateLibrary^>
	echo     ^<SpectralAnalysisLib^>RSSpecAna32N.dll^</SpectralAnalysisLib^>
	echo ^</RsiRaseAnalysisParametersDoc^>
) > "%analysis_params%"

REM Generate the InputSpecs XML file
set "input_specs=%parent_directory%\InputSpecs.xml"
(
	echo ^<?xml version="1.0" encoding="UTF-8"?^>
	echo ^<RsiRaseInputDoc^>
	echo     ^<InputType^>FOLDER_FILTER^</InputType^>
	echo     ^<FolderFilter^>%input_dir%\*.n42^</FolderFilter^>
	echo ^</RsiRaseInputDoc^>
) > "%input_specs%"

REM Generate the OutputSpecs XML file
set "output_specs=%parent_directory%\OutputSpecs.xml"
(
	echo ^<?xml version="1.0" encoding="UTF-8"?^>
	echo ^<RsiRaseOutputDoc^>
	echo     ^<OutputFolder^>%output_dir%^</OutputFolder^>
	echo ^</RsiRaseOutputDoc^>
) > "%output_specs%"

RsiRaseReplay.exe -i "%input_specs%" -p "%analysis_params%" -o "%output_specs%"

endlocal
