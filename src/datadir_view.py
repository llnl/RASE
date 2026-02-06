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
datadir_view.py - Module for creating and managing human-readable views of data directories.

This module provides functionality to create and maintain a human-readable representation
of a data directory structure where folder names are based on IDs. It uses symbolic links
on Unix-based systems and junctions on Windows to create a parallel view structure with
readable names.

This module assume RASE's standard folder structure:
SampledSpectra/
  detector1/
    scenario1/
      RASE-spectra/
      replay1/
        spectra/
        results/
      replay2/
        results/
      replay3/
        spectra/
        results/
        translatedResults/
    scenario2/
      RASE-spectra/
      replay2/
        results/
      replay4/
        spectra/
        results/
  detector2/
    scenario1/
      RASE-spectra/
where `detectorX`, `scenarioX`, and `replayX` are the IDs from the database for each element.

Symbolic links are created directly for the folders "RASE-spectra" and "replays". Any file that
may be present at the scenario or detector level will not appear in the view.
"""

import os
import platform
import shutil
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Protocol

# Protocols to define required attributes for detectors, scenarios, and replays
class DetectorProtocol(Protocol):
    """Protocol for detector-like objects with id and name attributes"""
    id: Union[int, str]
    name: str

class ScenarioProtocol(Protocol):
    """Protocol for scenario-like objects with id and get_label()"""
    id: Union[int, str]
    def get_label(self) -> str: ...

class ReplayProtocol(Protocol):
    """Protocol for replay-like objects with id and name attributes"""
    id: Union[int, str]
    name: str


class DataDirViewManager:
    """
    Manages the creation and maintenance of human-readable views of data directories.

    This class provides methods to create, update, and synchronize a view directory
    that mirrors the structure of a data directory but with human-readable names.
    """

    def __init__(self, data_dir: Union[str, Path],
                 view_dir: Union[str, Path],
                 detectors: List[DetectorProtocol],
                 scenarios: List[ScenarioProtocol],
                 replays: List[ReplayProtocol]) -> None:
        """
        Initialize the DataViewManager.

        :param data_dir: Path to the original data directory with ID-based folder names
        :param view_dir: Path where the human-readable view will be created
        :param detectors: List of detector objects with id and name attributes
        :param scenarios: List of scenario objects with id and get_label method
        :param replays: List of replay objects with id and name attributes
        """
        self.data_dir = Path(data_dir)
        self.view_dir = Path(view_dir)
        self.is_windows = platform.system() == "Windows"

        # Mappings from IDs to human-readable names
        self.detector_map: Dict[str, str] = {}
        self.scenario_map: Dict[str, str] = {}
        self.replay_map: Dict[str, str] = {}

        # Ensure the view directory exists
        os.makedirs(self.view_dir, exist_ok=True)

        # Initialize the mapping
        self.update_name_maps(detectors, scenarios, replays)

    @staticmethod
    def clean_name(name: str) -> str:
        """
        Clean a name to make it suitable for use as a folder name.

        :param name: The name to clean
        :return: A cleaned version of the name
        """
        # Replace invalid characters with underscores
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove leading/trailing whitespace and periods
        cleaned = cleaned.strip().strip('.')
        # Use a placeholder if the name is empty
        if not cleaned:
            cleaned = "unnamed"
        return cleaned

    def get_deconflicted_name(self, name_map: Dict[str, str], id_val: str, name: str) -> str:
        """
        Get a deconflicted name for an item, appending the ID if needed.

        :param name_map: Dictionary of existing ID to name mappings
        :param id_val: ID of the current item
        :param name: Proposed name for the item
        :return: A name that doesn't conflict with existing names
        """
        # Clean the name first
        clean_name = self.clean_name(name)

        # Remove the id from the map if already present
        if id_val in name_map:
            del name_map[id_val]

        # Check for conflicts with existing names
        conflicts = False
        for existing_id, existing_name in name_map.items():
            if existing_id != id_val and existing_name == clean_name:
                conflicts = True
                break

        # If there's a conflict, append the ID
        if conflicts:
            return f"{clean_name}_{id_val}"
        else:
            return clean_name

    def update_name_maps(self,
                         detectors: Optional[List[DetectorProtocol]] = None,
                         scenarios: Optional[List[ScenarioProtocol]] = None,
                         replays: Optional[List[ReplayProtocol]] = None) -> None:
        """
        Update the name mappings for detectors, scenarios, and replays.

        :param detectors: List of detector objects with id and name attributes
        :param scenarios: List of scenario objects with id and get_label method
        :param replays: List of replay objects with id and name attributes
        """
        # Update detector mappings
        if detectors:
            for detector in detectors:
                detector_id = str(detector.id)
                detector_name = detector.name
                self.detector_map[detector_id] = self.get_deconflicted_name(
                    self.detector_map, detector_id, detector_name)

        # Update scenario mappings
        if scenarios:
            for scenario in scenarios:
                scenario_id = str(scenario.id)
                scenario_label = scenario.get_label()
                self.scenario_map[scenario_id] = self.get_deconflicted_name(
                    self.scenario_map, scenario_id, scenario_label)

        # Update replay mappings
        if replays:
            for replay in replays:
                replay_id = str(replay.id)
                replay_name = replay.name
                self.replay_map[replay_id] = self.get_deconflicted_name(
                    self.replay_map, replay_id, replay_name)

    def add_map_item(self, target: str, id_: str, name: str) -> None:
        """
        Add an item to the specified map with a deconflicted name.

        :param target: The target map ('detector', 'scenario', or 'replay')
        :param id_: The ID of the item
        :param name: The name of the item
        """
        if target == 'detector':
            map_ = self.detector_map
        elif target == 'scenario':
            map_ = self.scenario_map
        elif target == 'replay':
            map_ = self.replay_map
        else:
            raise ValueError(f"Invalid target: {target}")
        map_[id_] = self.get_deconflicted_name(map_, id_, name)

    def _create_link(self, source: Path, target: Path) -> None:
        """
        Create a symbolic link or junction pointing to the source directory.

        :param source: The directory to link to
        :param target: The location where the link will be created
        """
        if target.exists():
            if target.is_dir() and not target.is_symlink() and not self._is_junction(target):
                shutil.rmtree(target)
            else:
                target.unlink()

        # Create parent directories if they don't exist
        os.makedirs(target.parent, exist_ok=True)

        if self.is_windows:
            # Use mklink /J for junctions on Windows
            subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(source)],
                           check=True, capture_output=True)
        else:
            # Use symbolic links on Unix-based systems
            os.symlink(source, target, target_is_directory=True)

    def update_detector(self, detector_id: str, new_name: str) -> None:
        """
        Update the view when a detector's name changes.

        :param detector_id: ID of the detector
        :param new_name: New name for the detector
        """
        # When creating a new detector, the db may call this method with detector_id=None
        if not detector_id:
            return

        detector_path = self.data_dir / detector_id
        if not detector_path.exists():
            return

        old_name = self.detector_map.get(detector_id, detector_id)
        new_label = self.get_deconflicted_name(self.detector_map, detector_id, new_name)
        # Update the mapping
        self.detector_map[detector_id] = new_label

        if old_name == new_label:
            return

        old_view_path = self.view_dir / old_name
        new_view_path = self.view_dir / new_label

        # If the old path exists and is different from the new path, update it
        if old_view_path.exists():
            old_view_path.rename(new_view_path)

    def delete_detector(self, detector_id: str) -> None:
        """
        Update the view when a detector is deleted.

        :param detector_id: ID of the detector to delete
        """
        # Get the name from the mapping
        detector_name = self.detector_map.get(detector_id, detector_id)
        view_path = self.view_dir / detector_name

        # Remove from the view
        if view_path.exists():
            if view_path.is_symlink() or (self.is_windows and self._is_junction(view_path)):
                view_path.unlink()
            else:
                shutil.rmtree(view_path)

        # Remove from the mapping
        if detector_id in self.detector_map:
            del self.detector_map[detector_id]

    def delete_scenario(self, scenario_id: str) -> None:
        """
        Update the view when a scenario is deleted across all detectors.

        :param scenario_id: ID of the scenario to delete
        """
        # deletion is global
        old_name = self.scenario_map.get(scenario_id, scenario_id)
        # Remove views under each detector
        for det_id in os.listdir(self.data_dir):
            det_name = self.detector_map.get(det_id, det_id)
            view_path = self.view_dir / det_name / old_name
            if view_path.exists():
                shutil.rmtree(view_path)
        # Remove from mapping
        self.scenario_map.pop(scenario_id, None)

    def delete_replay(self, replay_id: str) -> None:
        """
        Update the view when a replay is deleted across all detectors and scenarios.

        :param replay_id: ID of the replay to delete
        """
        # deletion is global
        old_name = self.replay_map.get(replay_id, replay_id)
        for det_id in os.listdir(self.data_dir):
            det_name = self.detector_map.get(det_id, det_id)
            det_view = self.view_dir / det_name
            if not det_view.exists():
                continue
            for scen_name in os.listdir(det_view):
                path = det_view / scen_name / old_name
                if path.exists():
                    shutil.rmtree(path)
        # update the mapping
        self.replay_map.pop(replay_id, None)

    def update_scenario(self, scenario_id: str, new_name: str) -> None:
        """
        Update the view when a scenarios' name changes.

        :param scenario_id: ID of the scenario
        :param new_name: New name for the scenario
        """
        if not scenario_id:
            return

        old_name = self.scenario_map.get(scenario_id, scenario_id)
        new_label = self.get_deconflicted_name(self.scenario_map, scenario_id, new_name)

        # update mapping
        self.scenario_map[scenario_id] = new_label

        if old_name == new_label:
            return

        # Update view
        for det_id in os.listdir(self.data_dir):
            det_path = self.data_dir / det_id
            if not det_path.is_dir():
                continue
            det_name = self.detector_map.get(det_id, det_id)
            old_view = self.view_dir / det_name / old_name
            new_view = self.view_dir / det_name / new_label
            if old_view.exists():
                old_view.rename(new_view)

    def update_replay(self, replay_id: str, new_name: str) -> None:
        """
        Update the view when a replay's name changes.

        :param replay_id: ID of the replay
        :param new_name: New name for the replay
        """
        # When creating a new replay, the db may call this method with replay_id=None
        if not replay_id:
            return

        old_name = self.replay_map.get(replay_id, replay_id)
        new_label = self.get_deconflicted_name(self.replay_map, replay_id, new_name)

        # Update mapping
        self.replay_map[replay_id] = new_label

        if old_name == new_label:
            return

        # Iterate detectors and scenarios
        for det_id in os.listdir(self.data_dir):
            det_path = self.data_dir / det_id
            if not det_path.is_dir():
                continue
            det_name = self.detector_map.get(det_id, det_id)
            for scen_id in os.listdir(det_path):
                scen_path = det_path / scen_id
                if not scen_path.is_dir():
                    continue
                scen_name = self.scenario_map.get(scen_id, scen_id)
                scen_view = self.view_dir / det_name / scen_name
                if not scen_view.exists():
                    continue
                old_view = scen_view / old_name
                new_view = scen_view / new_label
                if old_view.exists():
                    old_view.rename(new_view)

    def resync_full_view(self) -> None:
        """
        Create a complete human-readable view of the data directory from scratch.
        """
        # Clear existing view
        if self.view_dir.exists():
            shutil.rmtree(self.view_dir)
        os.makedirs(self.view_dir, exist_ok=True)

        # Create the view structure
        for detector_id in os.listdir(self.data_dir):
            detector_path = self.data_dir / detector_id

            detector_name = self.detector_map.get(detector_id, detector_id)
            view_detector_path = self.view_dir / detector_name

            self._create_detector_view(detector_path, view_detector_path)

    def resync_single_view(self, detector_id: str, scenario_id: str, replay_id: str | None = None):
        """
        Creates or resync a view for a (detector, scenario) or (detector, scenario, replay) combination

        :param detector_id: Detector ID
        :param scenario_id: Scenario ID
        :param replay_id: Replay ID. If None, then the view for the entire scenario is resynced
        """
        if not (detector_id and scenario_id):
            return

        detector_path = self.data_dir / detector_id
        detector_name = self.detector_map.get(detector_id, detector_id)
        view_detector_path = self.view_dir / detector_name

        scenario_path = detector_path / scenario_id
        scenario_name = self.scenario_map.get(scenario_id, scenario_id)
        view_scenario_path = view_detector_path / scenario_name

        if not replay_id:
            if view_scenario_path.exists():
                shutil.rmtree(view_scenario_path)
            self._create_scenario_view(scenario_path, view_scenario_path)
        else:
            self._create_rase_spectra_view(scenario_path, view_scenario_path)
            replay_path = scenario_path / replay_id
            replay_name = self.replay_map.get(replay_id, replay_id)
            view_replay_path = view_scenario_path / replay_name
            if view_replay_path.exists():
                shutil.rmtree(view_replay_path)
            self._create_replay_view(replay_path, view_replay_path)

    def get_view_dir(self, detector_id: str, scenario_id: str, replay_id: str | None = None) -> Path:
        """
        Get the path in the view directory corresponding to the given detector, scenario, and optional replay.

        :param detector_id: ID of the detector whose view folder is desired
        :param scenario_id: ID of the scenario under the detector
        :param replay_id: ID of the replay under the scenario; if None, returns the scenario view path
        :return: Path in the human-readable view directory for the specified item
        """
        view_scenario_path = (self.view_dir /
                              self.detector_map.get(detector_id, detector_id) /
                              self.scenario_map.get(scenario_id, scenario_id))
        if not replay_id:
            return view_scenario_path
        else:
            return view_scenario_path / self.detector_map.get(replay_id, replay_id)

    def _create_detector_view(self, detector_path: Path, view_path: Path) -> None:
        """
        Create a view for a single detector if detector_path exists

        :param detector_path: Path to the detector directory
        :param view_path: Path where the view will be created
        """
        if not detector_path.is_dir():
            return

        # Process scenarios
        for scenario_id in os.listdir(detector_path):
            scenario_path = detector_path / scenario_id

            scenario_name = self.scenario_map.get(scenario_id, scenario_id)
            view_scenario_path = view_path / scenario_name

            self._create_scenario_view(scenario_path, view_scenario_path)

    def _create_rase_spectra_view(self, scenario_path: Path, view_path: Path) -> None:
        """
        Create link for RASE-spectra if it exists

        :param scenario_path: Path to the scenario directory
        :param view_path: Path where the scenario view will be created
        """
        rase_spectra_path = scenario_path / "RASE-spectra"
        if rase_spectra_path.exists() and rase_spectra_path.is_dir():
            view_rase_spectra_path = view_path / "RASE-spectra"
            self._create_link(rase_spectra_path, view_rase_spectra_path)

    def _create_scenario_view(self, scenario_path: Path, view_path: Path) -> None:
        """
        Create a view for a single scenario if scenario_path exists

        :param scenario_path: Path to the scenario directory
        :param view_path: Path where the view will be created
        """
        if not scenario_path.is_dir():
            return

        self._create_rase_spectra_view(scenario_path, view_path)

        # Process replays
        for replay_id in os.listdir(scenario_path):
            if replay_id == "RASE-spectra":
                continue

            replay_path = scenario_path / replay_id

            replay_name = self.replay_map.get(replay_id, replay_id)
            view_replay_path = view_path / replay_name

            # Create links for replay subdirectories
            self._create_replay_view(replay_path, view_replay_path)

    def _create_replay_view(self, replay_path: Path, view_path: Path) -> None:
        """
        Create a view for a single replay if replay_path exists

        :param replay_path: Path to the replay directory
        :param view_path: Path where the view will be created
        """
        if not replay_path.is_dir():
            return

        # Create links for replay subdirectories
        for subdir in os.listdir(replay_path):
            subdir_path = replay_path / subdir
            if subdir_path.is_dir():
                view_subdir_path = view_path / subdir
                self._create_link(subdir_path, view_subdir_path)

    def _is_junction(self, path: Path) -> bool:
        """
        Check if a path is a Windows junction.

        :param path: Path to check
        :return: True if the path is a junction, False otherwise
        """
        if not self.is_windows or not path.exists():
            return False

        try:
            result = subprocess.run(
                ["cmd", "/c", "dir", "/al", str(path.parent)],
                capture_output=True, text=True, check=True
            )

            for line in result.stdout.splitlines():
                if path.name in line and "<JUNCTION>" in line:
                    return True
            return False
        except subprocess.SubprocessError:
            return False
