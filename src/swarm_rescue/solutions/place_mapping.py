"""Sensor-only wall evidence for the red team's first mapping baseline."""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

import numpy as np

from swarm_rescue.simulation.utils.constants import MAX_RANGE_LIDAR_SENSOR


class WallEvidenceMap:
    """Accumulate noisy lidar observations in a one-pixel world-aligned grid.

    Positive evidence means a likely wall; negative evidence means free space.
    The evidence is private working state. Only a binary grid is submitted.
    """

    _MAX_MAPPING_RANGE = 180.0
    _ENDPOINT_MARGIN = 8.0
    _FREE_END_MARGIN = 10.0
    _FREE_STEP = 5.0
    _RAY_STRIDE_FOR_FREE = 3
    _HIT_WEIGHT = 2
    _FREE_WEIGHT = -1
    _MIN_EVIDENCE = -8
    _MAX_EVIDENCE = 8
    _WALL_THRESHOLD = 3
    _HIT_RADIUS = 2
    _NONWALL_ANGLE_TOL = math.pi / 24  # 7.5 degrees
    _NONWALL_DISTANCE_TOL = 24.0

    def __init__(self, size_area: Tuple[int, int]):
        self.width, self.height = (int(size_area[0]), int(size_area[1]))
        if self.width <= 0 or self.height <= 0:
            raise ValueError("map dimensions must be positive")
        self.evidence = np.zeros((self.height, self.width), dtype=np.int16)
        self.observed_scans = 0
        self._hit_offsets = np.asarray(
            [
                (dr, dc)
                for dr in range(-self._HIT_RADIUS, self._HIT_RADIUS + 1)
                for dc in range(-self._HIT_RADIUS, self._HIT_RADIUS + 1)
                if dr * dr + dc * dc <= self._HIT_RADIUS * self._HIT_RADIUS
            ],
            dtype=np.int16,
        )

    def _add_evidence(self, rows: np.ndarray, cols: np.ndarray, value: int) -> None:
        inside = (
            (rows >= 0)
            & (rows < self.height)
            & (cols >= 0)
            & (cols < self.width)
        )
        rows, cols = rows[inside], cols[inside]
        if rows.size == 0:
            return
        np.add.at(self.evidence, (rows, cols), value)
        self.evidence[rows, cols] = np.clip(
            self.evidence[rows, cols], self._MIN_EVIDENCE, self._MAX_EVIDENCE
        )

    def _nonwall_returns(
        self,
        angles: np.ndarray,
        distances: np.ndarray,
        semantic_obstacles: Iterable[Tuple[float, float]],
    ) -> np.ndarray:
        nonwall = np.zeros(distances.shape, dtype=bool)
        for angle, distance in semantic_obstacles:
            if not (math.isfinite(angle) and math.isfinite(distance)):
                continue
            angle_error = (angles - angle + math.pi) % (2 * math.pi) - math.pi
            nonwall |= (
                (np.abs(angle_error) <= self._NONWALL_ANGLE_TOL)
                & (np.abs(distances - distance) <= self._NONWALL_DISTANCE_TOL)
            )
        return nonwall

    def update(
        self,
        position: Sequence[float],
        heading: float,
        distances: Sequence[float],
        relative_angles: Sequence[float],
        semantic_obstacles: Iterable[Tuple[float, float]] = (),
    ) -> None:
        """Fuse one scan; ignore invalid positions, rays and non-wall returns."""
        pos = np.asarray(position, dtype=float)
        values = np.asarray(distances, dtype=float)
        angles = np.asarray(relative_angles, dtype=float)
        if (
            pos.shape != (2,)
            or not np.all(np.isfinite(pos))
            or not math.isfinite(heading)
            or values.ndim != 1
            or angles.shape != values.shape
        ):
            return

        valid = np.isfinite(values) & np.isfinite(angles) & (values > 4.0)
        if not np.any(valid):
            return
        self.observed_scans += 1
        values, angles = values[valid], angles[valid]
        world_angles = angles + heading
        cosines, sines = np.cos(world_angles), np.sin(world_angles)
        nonwall = self._nonwall_returns(angles, values, semantic_obstacles)

        # Stop short of a hit so pose noise does not carve through the wall.
        free_values = values[:: self._RAY_STRIDE_FOR_FREE]
        free_cos = cosines[:: self._RAY_STRIDE_FOR_FREE]
        free_sin = sines[:: self._RAY_STRIDE_FOR_FREE]
        free_limit = np.maximum(
            0.0,
            np.minimum(free_values, self._MAX_MAPPING_RANGE)
            - self._FREE_END_MARGIN,
        )
        samples = np.arange(self._FREE_STEP, self._MAX_MAPPING_RANGE, self._FREE_STEP)
        free_mask = samples[None, :] < free_limit[:, None]
        xs = pos[0] + free_cos[:, None] * samples[None, :]
        ys = pos[1] + free_sin[:, None] * samples[None, :]
        free_cols = np.rint(xs + self.width / 2).astype(np.int32)
        free_rows = np.rint(-ys + self.height / 2).astype(np.int32)
        self._add_evidence(free_rows[free_mask], free_cols[free_mask], self._FREE_WEIGHT)

        hits = (
            (values < min(MAX_RANGE_LIDAR_SENSOR - self._ENDPOINT_MARGIN,
                          self._MAX_MAPPING_RANGE))
            & ~nonwall
        )
        if not np.any(hits):
            return
        hit_x = pos[0] + values[hits] * cosines[hits]
        hit_y = pos[1] + values[hits] * sines[hits]
        centers_col = np.rint(hit_x + self.width / 2).astype(np.int32)
        centers_row = np.rint(-hit_y + self.height / 2).astype(np.int32)
        rows = centers_row[:, None] + self._hit_offsets[None, :, 0]
        cols = centers_col[:, None] + self._hit_offsets[None, :, 1]
        self._add_evidence(rows.ravel(), cols.ravel(), self._HIT_WEIGHT)

    def binary_wall_grid(self) -> np.ndarray:
        """Return the exact-resolution grid required by submit_exploration_map."""
        return (self.evidence >= self._WALL_THRESHOLD).astype(np.uint8)
