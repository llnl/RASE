:: This Windows script is a wrapper for the BTI FlexSpec X5600 Replay Tool
:: Place this script in the same folder as N42Replay.exe
:: 2024-05-21 Steven Czyz <czyz1@llnl.gov>, building off work by Samuele Sangiorgio <sangiorgio1@llnl.gov>

@ECHO OFF
SETLOCAL ENABLEEXTENSIONS

:: execute from the parent folder
cd /d %~dp0

:: Check command line input. Expect input and output folders
SET missing_param=0
IF [%1]==[] SET missing_param=1
IF [%2]==[] SET missing_param=1
echo %1
echo %2
IF /I %missing_param% EQU 1 (
  ECHO Usage: %~n0 -a MANUAL_OCCUPANCY input_folder -o output_folder
  EXIT /B 1
)

N42Replay.exe -a MANUAL_OCCUPANCY %1 -o %2

:: Moving results to output folder
:: Note that this fails if %2 already exists as a file
IF NOT EXIST %2\ (mkdir %2)

for /r %2 %%F in (*.n42) do (
    echo %%~nxF | find /I "_STREAMING" >nul
    if errorlevel 1 (
        move "%%F" %2 >nul
    ) else (
         del "%%F"
     )
)
for /r %2 %%F in (*.txt *.csv) do (
    del "%%F"
)
for /d /r %2 %%D in (*) do (
    rd /s /q "%%D"
)
