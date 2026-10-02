"""Stable, simulator-independent contracts for replaceable strategy modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Tuple

import numpy as np

Point = Tuple[float, float]


@dataclass(frozen=True)
class Observation:
    step: int
    position: Optional[Point]
    heading: Optional[float]
    velocity: Point
    lidar: np.ndarray
    angles: np.ndarray
    inventory: int
    nonwalls: Tuple[Tuple[float, float], ...] = ()
    bomb_returns: Tuple[Tuple[float, float], ...] = ()


@dataclass(frozen=True)
class Goal:
    position: Point
    source: str


@dataclass(frozen=True)
class NavResult:
    status: str
    forward: float = 0.0
    lateral: float = 0.0
    rotation: float = 0.0


@dataclass(frozen=True)
class BombEvent:
    owner: int
    sequence: int
    position: Point
    step: int


@dataclass(frozen=True)
class PeerState:
    identifier: int
    step: int
    position: Optional[Point]
    inventory: int
    phase: str
    goal: Optional[Point] = None
    anchor: Optional[Point] = None


@dataclass(frozen=True)
class MapSnapshot:
    """Arrays are read-only; world x right, y up; row down, col right."""
    version: int
    size: Tuple[int, int]
    resolution: int
    wall_grid: np.ndarray
    known: np.ndarray
    blocked: np.ndarray
    wall_mass: np.ndarray

    def contains(self, point: Point) -> bool:
        width, height = self.size
        return (-width / 2 <= point[0] < width / 2
                and -height / 2 < point[1] <= height / 2)

    def cell(self, point: Point) -> Tuple[int, int]:
        x, y = point
        width, height = self.size
        return (
            int(np.clip((height / 2 - y) / self.resolution, 0, self.known.shape[0] - 1)),
            int(np.clip((x + width / 2) / self.resolution, 0, self.known.shape[1] - 1)),
        )

    def world(self, cell: Tuple[int, int]) -> Point:
        row, col = cell
        width, height = self.size
        return ((col + .5) * self.resolution - width / 2,
                height / 2 - (row + .5) * self.resolution)


class ExplorerBackend(Protocol):
    """A teammate may replace this without implementing the drone API."""
    anchor: Optional[Point]
    def update(self, observation: Observation) -> None: ...
    def ingest(self, source: int, version: int, payload: bytes) -> None: ...
    def map_delta(self) -> Optional[Tuple[int, int, bytes]]: ...
    def snapshot(self) -> MapSnapshot: ...
    def next_goal(self, observation: Observation, navigator: "NavigatorBackend",
                  peers: Mapping[int, PeerState]) -> Optional[Goal]: ...
    def reject(self, goal: Goal, step: int) -> None: ...
    def export_wall_grid(self) -> np.ndarray: ...


class NavigatorBackend(Protocol):
    def distance_field(self, start: Point, snapshot: MapSnapshot) -> np.ndarray: ...
    def estimate_cost(self, start: Point, goal: Point, snapshot: MapSnapshot) -> float: ...
    def step(self, goal: Goal, observation: Observation,
             snapshot: MapSnapshot) -> NavResult: ...
    def reset(self) -> None: ...
