RASE - Replicative Assessment of Spectroscopic Equipment
========================================================

RASE is a software for evaluating the performance of radiation detectors and isotope identification algorithms.
It uses a semi-empirical approach to rapidly generate synthetic spectra and inject into detector’s software
to obtain nuclide identification response.

For more information on RASE see:
* [R. Arlt et al, IEEE NSS Conf Record, 2009](https://doi.org/10.1109/NSSMIC.2009.5402448)

Using RASE and getting started quickly
--------------------------------------
RASE is distributed with example detectors, spectra, and tables that are designed to get users up and running as quickly as possible. These files are accessible via the `examples` folder in the RASE .zip release package or in the source code. Please consult the Quick Start Guide in the RASE manual for details on how to use these files. The manual is accessible via the `help` menu or via the pdf version, accessible via the releases tab.

Utilizing the RASE API
----------------------
RASE 3.0 is released with an API that enables users to execute key aspects of the RASE workflow using python scripts and .yaml config files. Documentation for the API is in progress; in the meantime, the `example_api_workflow.py`, `example_api_scurves.py`, and `example_api_backgrounds.py` sample scripts in the `demonstrationScripts` directory outline some of the most widely used functionality. Corresponding .yaml files can be found in the `examples` directory as `example_api_backgrounds.yaml` and `example_api_scurves.yaml`. Using the RASE API requires several libraries, detailed below. 

Required Libraries
------------------
* BeautifulSoup4
* declxml
* isodate
* lmFit
* lxml
* mako
* marshmallow-sqlalchemy
* matplotlib 
* numpy
* pandas
* pyside6
* pyyaml
* qt6
* requests
* scikit-learn
* scipy=
* seaborn
* SQLAlchemy
* tqdm
* uncertainties

* pytest (for unit testing)
* pytest-qt (for unit testing)
* Sphinx (for docs development)

The relevant packages can be conveniently installed using `pip`.

Creating a standalone executable
--------------------------------
[PyInstaller](http://www.pyinstaller.org/) can be used to generate a standalone executable for distribution on Windows
operating systems.

Note that PyInstaller is rather sensitive to the overall python configuration. These instructions assume a clean
python environment with the minimal set of python packages installed. We recommend starting with a clean empty python environment 
(e.g. using WinPythonZero)

* Install pyinstaller and pypiwin32 packages via `pip install pyinstaller pypiwin32`
* The file `rase.spec` contains the specifications to create a single executable file `dist\rase.exe`.
* Run `pyinstaller -a -y rase.spec`  or `python create_distributable.py` from the RASE base folder


Generating documentation with Sphinx
------------------------------------
RASE documentation is maintained using [Sphinx](http://www.sphinx-doc.org/en/stable/).
The documentation resides in the `doc` folder.

Install Sphinx from PyPi using
`$ pip install Sphinx`

<!-- For referencing figures by number it is required to install the numfig extension for Sphinx. -->
<!-- Installation is performed with the following steps: -->
<!-- 1. Download and untar the file at this [link](https://sourceforge.net/projects/numfig/files/Releases/sphinx_numfig-r13.tgz/download) -->
<!-- 1. Run `2to3 -w setup.py` -->
<!-- 1. Run `python setup.py install` -->

To update the documentation:
1. `cd $RASE\doc`, where `$RASE` is RASE base folder where rase.pyw lives
1. `make html` to generate html docs
1. `make latexpdf` to generate latex docs and immediately compile the pdf

The documentation is generated in the `doc\_build\` folder

Updating Language Translations Files
------------------------------------

RASE uses QT Linguist and its related tools to provide translations of the application in different languages.

The process to create a new language file or update and existing one is as follows:
1. Ensure the source code is ready for translation. See [QT Manual](https://doc.qt.io/qt-6/i18n-source-translation.html)
2. `cp rase.pyw rase.py`  This  step is necessary due to a bug in QT's `lupdate` code which does not process `.pyw` files correctly.
3. `pyside6-lupdate -no-obsolete rase.py src/*.py src/ui/*.ui -ts translations/rase_LANG.ts`  where `LANG` should be replaced with the ISO 639 language code. 
4. Provide translations for the source texts in the `.ts` file using `Qt Linguist` or directly with a text editor. Multiple `.ts` language files can be specified.
5. Run `lrelease translations/*.ts`
6. Test by temporarily setting the locale e.g. running the following from the terminal `LC_ALL=it_IT.UTF-8 python rase.pyw`
7. `rm rase.py`


Contributors
------------

- Lance Bentley-Tammero, LLNL
- Jason Brodsky, LLNL
- Joe Chavez, LLNL
- Steven Czyz, LLNL
- Greg Kosinovsky, LLNL
- Vladimir Mozin, LLNL
- Samuele Sangiorgio, LLNL

Citation
--------

Please cite use of the RASE software as:

L. Bentley-Tammero, J. P. Brodsky, J. Chavez, S. A. Czyz, G. Kosinovsky, V. Mozin, & S. Sangiorgio. 
(2024, Dec 5). LLNL/RASE: RASE v3.0 (Version v3.0). Zenodo. http://doi.org/10.5281/zenodo.14285934


Acknowledgements
----------------

This work was performed by Lawrence Livermore National Laboratory under the auspices
of the U.S. Department of Energy under contract DEJAC52J07NA27344,
and of the U.S. Department of Homeland Security Domestic Nuclear Detection Office
under contract HSHQDC-15-X-00128.

Lawrence Livermore National Laboratory (LLNL) gratefully acknowledges support from
the U.S. Department of Energy (DOE) Nuclear Smuggling Detection and Deterrence
program and from the Countering Weapons of Mass Destruction Office of the U.S.
Department of Homeland Security.


License
-------

RASE is released under an MIT license and LGPL License. For more details see the [LICENSE]
(/LICENSE-MIT) and [LICENSE](/LICENSE-LGPL) files.

LLNL-CODE-2001375, LLNL-CODE-829509
