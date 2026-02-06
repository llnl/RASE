.. _release_notes:

******************
RASE release notes
******************

RASE v3.1
=========

- Updated shielding algorithm and features

    - Apply shielding as a scenario effect
    - Shielding can be interpolated/extrapolated to arbitrary thickness
    - Auto S-curve can vary shielding thickness at a fixed source intensity
    - Reduced oscillation behavior

- Tool for removing isotope ID results from experimental data
- Tool for converting spectra between detector formats
- Directory structure refactor for easier human parsing
- Default correspondence table loading
- Improved internationalization, including interface translation files for German, Italian, Spanish
- Improved S-curve algorithm stability
- Various code refactors and bug fixes
- Documentation updates


RASE v3.0
=========

- RASE API for use with custom Python scripts

    - Create detectors and replay tools
    - Create scenarios and run simulations
    - Auto S-curve generation
    - Include example scripts

- Apply shielding effects to base spectra

    - Provide pre-built shielding libraries for nine common materials at several thicknesses
    - Include detector response for 512, 1024, 2048, and 3000 channel detectors

- Detector/replay tool separation

    - Allow one replay tool to run with any number of detectors, and vice versa

- Weight isotope ID results by reported confidence
- Support single-bin neutron scaling and sampling from base spectra
- Support multi-volume detectors in base spectra creation and spectra generation
- Refactor code to support RASE internationalization
- Expand base spectra configurations and n42 template libraries; update and expand replay tool documentation
- Various bug fixes
- Documentation updates, including a quick start guide


RASE v2.4
=========

- Add detector import/export functionality
- Enable instrument cloning
- Allow renaming of detectors and replay tools
- Add a base spectrum creation wizard
- Expand base spectrum template library
- Allow summing of sample spectra for visualization, comparison, and export
- Improve secondary spectrum handling

    - Simultaneously define on-board background and internal source spectra
    - Allow base spectra to include multiple secondary spectra
    - Specify dwell time and sampling behavior for secondary background

- Improve compatibility with FullSpec WebID replay tool

    - Improve DRF selection
    - Point web address to the appropriate URL

- Export results improvements

    - Include detailed ID results in exports
    - Export results in JSON format

- Automatically translate isotope ID results for FLIR, Symetrica, Kromek, and RadSeeker replay tools, as well
  as instruments outputting in the standard n42-2011 format.
- Include Python script compatible with GADRAS 19.3.3 API that creates base spectra for a user-specified
  instrument from the source list in an exported RASE detector file.
- Various bug fixes
- Documentation updates


RASE v2.3
=========

- Integrate with Full Spectrum Web ID directly from RASE
- Refactor base spectra creation tool:

    - Convert to config-file-based operation for ease of use
    - Add support for PCF files
    - Ingest PeakEasy/Interspec output

- Improve robustness of S-curve fitting
- Allow manual adjustment of S-curve fit parameters from the GUI
- Add dose-to-distance conversion in plots and scenario creation
- Initial support for backgrounds with inseparable internal sources
- Accept base spectra with different calibration coefficients


RASE v2.2
=========

- Improved plotting capabilities

  - 1D histograms
  - 3D results heat maps

- Add isotope ID frequency analysis and plotting
- Extensively update base spectra collection guidance documentation
- Add Kromek D5 replay tool documentation, template, and translator
- Improvements to development and testing capabilities

  - Add unit test suite for developers

- Various bug fixes
- Documentation updates


RASE v2.1
=========

- Better secondary spectrum handling

  - Allow internal background to be taken directly from a scenario definition or from a specific base spectrum

- Influences redesign

  - Allow users to define energy resolution degradation
  - Allow calibration coefficients and energy resolution terms to vary over time to model environmental
    effects

- Include a set of "code evaluation" base spectra with standard shapes, such as "delta", "flat", and
  "sawtooth"
- Weighted F-score
- Import experimental spectra into the RASE workflow
- Improve internal project switching
- Improve internal spectra viewer
- Add statistics for detailed ID results
- Various bug fixes
- Documentation updates, including GADRAS isotope ID replay tool documentation


RASE v2.0
=========

- Automated S-curve generation tool added

  - Automatic S-range finding and high-statistics scenario creation
  - Support an arbitrary number of static backgrounds (e.g., masking scenarios)
  - Support regular and inverted S-curves

- Improve plotting options
- Scenario group redesign:

  - Allow scenarios to exist in multiple groups simultaneously
  - Support bulk scenario selection for group changes
  - Allow creating scenarios based on existing scenarios
  - Allow adding and deleting groups freely

- Add automatic scenario range generation tool
- Streamline import of scenarios defined in .csv files
- Various bug fixes
- Documentation updates


RASE v1.2
=========
- Improve scenario results table to provide:

  - More results information
  - User-customizable column display settings
  - Sorting capabilities
  - Source separation for multi-isotope scenarios

- Support multi-instrument selection and scenario execution
- Enable full workflow execution via a single button
- Add flux sensitivity unit
- Implement generic plotting features
- Add S-curve fitting
- Various bug fixes
- Documentation updates


RASE v1.1
=========

- Add base spectra creation tool
- Make most file/folder browsing dialogs open in the last visited folder
- Allow editing replay tool details by double-clicking an entry in the Manage Replay Tools dialog
- Retain scenario group selection across operations
- Improve results table sorting
- Update documentation
- Other minor bug fixes and clean-up


RASE v1.0
=========

- Add new background treatment in the workflow
- Add compatibility with instruments from the INL-2018 data collection event and integrate replay tools from
  various vendors
- Improve Correspondence table and results analysis logic
- Add random seed control
- Refactor file handling to accept more formats for base spectra and results files
- Implement base spectra generation methods
- Extend the "Help" section with instructions and examples
- Make multiple code and UI modifications to improve the workflow
- Extensive bug fixes and error intercepts