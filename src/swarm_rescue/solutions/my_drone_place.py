"""Red-team M0: retain safe roaming while submitting a sensor-built wall map."""

from __future__ import annotations

import math
from typing import Optional

from swarm_rescue.simulation.drone.controller import CommandsDict
from swarm_rescue.solutions.my_drone_place_example import MyDronePlaceExample
from swarm_rescue.solutions.place_mapping import WallEvidenceMap


class MyDronePlace(MyDronePlaceExample):
    """Each drone keeps its own wall evidence; drone 0 normally submits."""

    _MAP_EVERY_STEPS = 4
    _MIN_EXPLORE_FRACTION = 0.42
    _STEP_DEADLINE_MARGIN = 0.05
    _WALLTIME_DEADLINE_MARGIN = 0.10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wall_map: Optional[WallEvidenceMap] = (
            WallEvidenceMap(self.size_area) if self.size_area is not None else None
        )

    def _update_wall_map(self) -> None:
        if self._wall_map is None or self._steps % self._MAP_EVERY_STEPS:
            return
        position = self.measured_gps_position()
        heading = self.measured_compass_angle()
        lidar = self.lidar_values()
        if position is None or heading is None or lidar is None:
            return

        semantic_obstacles = []
        for hit in self.semantic_values() or []:
            entity = getattr(getattr(hit, "entity_type", None), "name", None)
            if entity in {"BOMB", "DRONE", "DISPOSAL_CENTER", "OTHER"}:
                semantic_obstacles.append((float(hit.angle), float(hit.distance)))
        self._wall_map.update(
            position,
            float(heading),
            lidar,
            self.lidar_rays_angles(),
            semantic_obstacles,
        )

    def _safety_deadline_reached(self) -> bool:
        if self._misc_data is None:
            return False
        step_limit = self._misc_data.max_timestep_limit
        walltime_limit = self._misc_data.max_walltime_limit
        if step_limit is not None and self.elapsed_timestep >= (
            1.0 - self._STEP_DEADLINE_MARGIN
        ) * step_limit:
            return True
        if walltime_limit is not None and self.elapsed_walltime >= (
            1.0 - self._WALLTIME_DEADLINE_MARGIN
        ) * walltime_limit:
            return True
        return False

    def _ready_to_submit(self) -> bool:
        if self._wall_map is None or self._exploration_submitted:
            return False
        if self._safety_deadline_reached():
            # Any surviving drone can rescue a round if the leader is unavailable.
            return True
        if not self._is_leader() or not self._all_teammates_report_zero_inventory():
            return False
        step_limit = (
            self._misc_data.max_timestep_limit if self._misc_data is not None else None
        )
        minimum_steps = (
            math.ceil(self._MIN_EXPLORE_FRACTION * step_limit)
            if step_limit is not None
            else 300
        )
        return self.elapsed_timestep >= minimum_steps

    def control(self) -> CommandsDict:
        self._steps += 1
        self._update_wall_map()
        self._sync_peer_inventory_from_messages()
        if self._ready_to_submit():
            self.submit_exploration_map(self._wall_map.binary_wall_grid())
            self._exploration_submitted = True
            return self._empty_command()

        command = self._control_roam()
        self._maybe_place_bomb(command)
        return command
