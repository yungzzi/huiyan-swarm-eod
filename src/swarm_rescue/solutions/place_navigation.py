"""Known-free-space search and holonomic feedback control, shared by both phases."""
from __future__ import annotations

import heapq
import math
from typing import Optional

import numpy as np

from swarm_rescue.solutions.place_types import Goal, MapSnapshot, NavResult, Observation, Point


class Navigator:
    def __init__(self):
        self._key = None
        self._dist = None
        self._parents = {}
        self._goal = None
        self._path = []
        self._path_step = -100
        self._last_progress_step = 0
        self._progress_position = None

    def reset(self):
        self._goal = None
        self._path = []
        self._progress_position = None

    def distance_field(self, start: Point, snapshot: MapSnapshot):
        origin = snapshot.cell(start)
        key = (snapshot.version, origin)
        if key == self._key:
            return self._dist
        walkable = self._walkable(origin, snapshot)
        dist = np.full(walkable.shape, np.inf)
        dist[origin] = 0.0
        queue = [(0.0, origin)]
        parents = {}
        height, width = walkable.shape
        while queue:
            cost, (r, c) = heapq.heappop(queue)
            if cost > dist[r, c]:
                continue
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < height and 0 <= nc < width and walkable[nr, nc]):
                    continue
                if dr and dc and not (walkable[r, nc] and walkable[nr, c]):
                    continue  # no cutting a wall corner
                candidate = cost + snapshot.resolution * math.hypot(dr, dc)
                if candidate < dist[nr, nc]:
                    dist[nr, nc] = candidate
                    parents[(nr, nc)] = (r, c)
                    heapq.heappush(queue, (candidate, (nr, nc)))
        self._key, self._dist, self._parents = key, dist, parents
        return dist

    def estimate_cost(self, start, goal, snapshot):
        if not snapshot.contains(start) or not snapshot.contains(goal):
            return math.inf
        return float(self.distance_field(start, snapshot)[snapshot.cell(goal)])

    def step(self, goal, observation, snapshot):
        if observation.position is None or observation.heading is None:
            return NavResult("unavailable")
        position = np.asarray(observation.position)
        if self._goal != goal:
            self._goal = goal
            self._path = []
            self._last_progress_step = observation.step
            self._progress_position = position.copy()
        delta = np.asarray(goal.position) - position
        distance = float(np.linalg.norm(delta))
        velocity = np.asarray(observation.velocity)
        if distance < 12:
            # Brake rather than coast through a placement target.
            local = self._local(-.22 * velocity, observation.heading)
            return NavResult("reached", *np.clip(local, -.6, .6))
        if np.linalg.norm(position - self._progress_position) > 12:
            self._progress_position = position.copy()
            self._last_progress_step = observation.step
        if observation.step - self._last_progress_step > 100:
            return NavResult("unreachable")

        target = snapshot.cell(goal.position)
        start = snapshot.cell(observation.position)
        if (not self._path or observation.step - self._path_step >= 40
                or any(snapshot.blocked[cell] for cell in self._path[1:])):
            self._path = self._astar(start, target, snapshot)
            self._path_step = observation.step
        if not self._path:
            return NavResult("unreachable")
        points = np.asarray([snapshot.world(cell) for cell in self._path])
        nearest = int(np.argmin(np.linalg.norm(points - position, axis=1)))
        waypoint = np.asarray(goal.position)
        for candidate in points[nearest + 1:]:
            waypoint = candidate
            if np.linalg.norm(candidate - position) >= 35:
                break
        if nearest >= len(points) - 2:
            waypoint = np.asarray(goal.position)
        vector = waypoint - position
        magnitude = np.linalg.norm(vector)
        if magnitude < 1:
            return NavResult("moving")
        world_command = vector / magnitude * min(.8, distance / 28) - .16 * velocity
        local = self._local(world_command, observation.heading)
        local = self._avoid(local, observation)
        norm = np.linalg.norm(local)
        if norm > .9:
            local *= .9 / norm
        return NavResult("moving", float(local[0]), float(local[1]))

    @staticmethod
    def _walkable(start, snapshot):
        walkable = (snapshot.known & ~snapshot.blocked).copy()
        r, c = start
        # Relax inflation only in the sensor-known, raw-wall-free footprint
        # around the current pose. Neither unknown space nor measured walls
        # are opened to make a route appear reachable.
        r0, r1 = max(0, r - 1), min(walkable.shape[0], r + 2)
        c0, c1 = max(0, c - 1), min(walkable.shape[1], c + 2)
        patch = snapshot.known[r0:r1, c0:c1] & (snapshot.wall_mass[r0:r1, c0:c1] == 0)
        walkable[r0:r1, c0:c1] |= patch
        walkable[start] = True
        return walkable

    @staticmethod
    def _astar(start, target, snapshot):
        """Search only the current route; full fields are for task selection."""
        walkable = Navigator._walkable(start, snapshot)
        if not walkable[target]:
            return []
        height, width = walkable.shape
        queue = [(0., 0., start)]
        costs, parents = {start: 0.}, {}
        while queue:
            _, cost, (r, c) = heapq.heappop(queue)
            if cost > costs[(r, c)]:
                continue
            if (r, c) == target:
                path = [target]
                while path[-1] != start:
                    path.append(parents[path[-1]])
                return path[::-1]
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < height and 0 <= nc < width and walkable[nr, nc]):
                    continue
                if dr and dc and not (walkable[r, nc] and walkable[nr, c]):
                    continue
                candidate = cost + math.hypot(dr, dc)
                if candidate < costs.get((nr, nc), math.inf):
                    costs[(nr, nc)] = candidate
                    parents[(nr, nc)] = (r, c)
                    heuristic = math.hypot(nr - target[0], nc - target[1])
                    heapq.heappush(queue, (candidate + heuristic, candidate, (nr, nc)))
        return []

    @staticmethod
    def _local(vector, heading):
        c, s = math.cos(heading), math.sin(heading)
        return np.array([c * vector[0] + s * vector[1],
                         -s * vector[0] + c * vector[1]])

    @staticmethod
    def _avoid(local, observation):
        valid = np.isfinite(observation.lidar) & (observation.lidar > 0)
        if not valid.any() or np.linalg.norm(local) < .01:
            return local
        distances = observation.lidar[valid].copy()
        angles = observation.angles[valid]
        for angle, distance in observation.bomb_returns:
            error = (angles - angle + math.pi) % (2 * math.pi) - math.pi
            distances[(np.abs(error) < math.pi / 18)
                      & (np.abs(distances - distance) < 18)] = 300
        bearing = math.atan2(local[1], local[0])
        error = (angles - bearing + math.pi) % (2 * math.pi) - math.pi
        cone = np.abs(error) < .35
        clearance = np.min(distances[cone]) if cone.any() else 300
        # A repulsive term acts in every movement direction, including reverse.
        near = distances < 42
        if near.any():
            weights = (42 - distances[near]) / 42
            repulsion = np.array([np.mean(np.cos(angles[near]) * weights),
                                  np.mean(np.sin(angles[near]) * weights)])
            local = local - .75 * repulsion
        if clearance < 25:
            local *= .35
        return np.clip(local, -.85, .85)
