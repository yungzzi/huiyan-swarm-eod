"""Marginal wall coverage, reachable goals, leases and confirmed bomb events."""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from swarm_rescue.solutions.place_types import BombEvent, Goal


class BombPlanner:
    MIN_SEPARATION = 64.0  # 24 official pixels plus pose/recording uncertainty

    def __init__(self, identifier, team_size, radius_ratio=.12):
        self.identifier, self.team_size = identifier, team_size
        self.radius_ratio = radius_ratio
        self.events = {}
        self.goal = None
        self._pending = None
        self._sequence = 0
        self._last_attempt = -100
        self._failed = {}

    def ingest(self, events):
        for event in events:
            if (isinstance(event, BombEvent)
                    and 0 <= event.owner < self.team_size
                    and len(event.position) == 2
                    and all(math.isfinite(x) for x in event.position)):
                self.events.setdefault((event.owner, event.sequence), event)

    def confirm(self, observation):
        if self._pending is None:
            return None
        old_inventory, position, step = self._pending
        if observation.step <= step:
            return None
        self._pending = None
        if observation.inventory < old_inventory:
            self._sequence += 1
            event = BombEvent(self.identifier, self._sequence, position, step)
            self.events[(event.owner, event.sequence)] = event
            self.goal = None
            return event
        if self.goal is not None:
            self._failed[self.goal.position] = observation.step + 200
        self.goal = None
        return None

    def reject(self, goal, step):
        self._failed[goal.position] = step + 200
        self.goal = None

    def choose_goal(self, snapshot, observation, navigator, peers, deadline):
        if observation.position is None or observation.inventory <= 0:
            return None
        if self.goal is not None:
            return self.goal
        mass = snapshot.wall_mass.copy()
        rr, cc = np.indices(mass.shape)
        radius = max(1, round(self.radius_ratio * min(snapshot.size) / snapshot.resolution))
        reservations = [event.position for event in self.events.values()]
        for peer in peers.values():
            if peer.phase == "PLACE" and peer.goal and observation.step - peer.step <= 120:
                reservations.append(peer.goal)
        allowed = snapshot.known & ~snapshot.blocked
        for point in reservations:
            r, c = snapshot.cell(point)
            square = (rr - r) ** 2 + (cc - c) ** 2
            mass[square <= radius ** 2] = 0
            allowed &= square * snapshot.resolution ** 2 >= self.MIN_SEPARATION ** 2
        for point, expiry in self._failed.items():
            if expiry > observation.step:
                r, c = snapshot.cell(point)
                allowed &= (rr - r) ** 2 + (cc - c) ** 2 > 4
        field = navigator.distance_field(observation.position, snapshot)
        # Reserve conservative movement time and one pulse/confirmation per bomb.
        available = max(0, deadline - observation.step - 20 * observation.inventory)
        allowed &= np.isfinite(field) & (field < available * 1.5)
        if not allowed.any():
            # Current physically occupied position is a zero-travel fallback;
            # lidar must confirm local clearance, and event spacing still holds.
            lidar = observation.lidar[np.isfinite(observation.lidar)]
            separated = all(np.linalg.norm(np.asarray(p) - observation.position)
                            >= self.MIN_SEPARATION for p in reservations)
            if (available > 6 and separated and lidar.size and np.min(lidar) > 18
                    and self._failed.get(observation.position, -1) <= observation.step):
                self.goal = Goal(observation.position, "place")
            return self.goal
        kr, kc = np.mgrid[-radius:radius + 1, -radius:radius + 1]
        kernel = ((kr ** 2 + kc ** 2) <= radius ** 2).astype(float)
        gain = ndimage.convolve(mass, kernel, mode="constant")
        normalizer = max(1.0, float(gain[allowed].max()))
        score = gain / normalizer - .0015 * field
        score[~allowed] = -np.inf
        r, c = np.unravel_index(np.argmax(score), score.shape)
        self.goal = Goal(snapshot.world((int(r), int(c))), "place")
        return self.goal

    def request(self, navigation, observation):
        if (navigation.status != "reached" or observation.inventory <= 0
                or self._pending is not None or observation.position is None
                or observation.step - self._last_attempt < 6
                or np.linalg.norm(observation.velocity) > .9):
            return False
        if any(np.linalg.norm(np.asarray(e.position) - observation.position)
               < self.MIN_SEPARATION for e in self.events.values()):
            self.goal = None
            return False
        self._pending = (observation.inventory, observation.position, observation.step)
        self._last_attempt = observation.step
        return True

    @property
    def pending(self):
        return self._pending is not None
