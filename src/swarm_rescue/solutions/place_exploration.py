"""GPS-assisted frontier exploration with source-versioned map exchange."""
from __future__ import annotations

import math
import zlib

import numpy as np
from scipy import ndimage

from swarm_rescue.solutions.place_mapping import WallEvidenceMap
from swarm_rescue.solutions.place_types import Goal, MapSnapshot


def pool(array, resolution, reduction):
    h, w = array.shape
    ph, pw = (-h) % resolution, (-w) % resolution
    padded = np.pad(array, ((0, ph), (0, pw)))
    blocks = padded.reshape((h + ph) // resolution, resolution,
                            (w + pw) // resolution, resolution)
    return reduction(reduction(blocks, axis=3), axis=1)


class Explorer:
    """Each origin's new map replaces its old contribution, including corrections."""
    RESOLUTION = 16

    def __init__(self, size, identifier, team_size):
        self.size = tuple(map(int, size))
        self.identifier, self.team_size = identifier, team_size
        self.local = WallEvidenceMap(self.size)
        self._parts = {}
        self._packets = {}
        self._snapshot = None
        self._version = 0
        self._relay_index = 0
        self._blacklist = {}
        self.anchor = None
        self._goal = None
        self._goal_step = 0

    def update(self, observation):
        if observation.position is None or observation.heading is None:
            return
        if self.anchor is None:
            self.anchor = observation.position
        if observation.step % 4 == 0:
            self.local.update(observation.position, observation.heading,
                              observation.lidar, observation.angles, observation.nonwalls)
        if observation.step % 24 == 0 or not self._parts:
            part = self.local.evidence.astype(np.int8)
            version = observation.step
            self._parts[self.identifier] = (version, part)
            self._packets[self.identifier] = (self.identifier, version,
                                              zlib.compress(part.tobytes(), 1))
            self._version += 1
            self._snapshot = None

    def ingest(self, source, version, payload):
        if not (isinstance(source, int) and 0 <= source < self.team_size
                and source != self.identifier and isinstance(version, int)
                and version >= 0 and isinstance(payload, bytes)):
            return
        old = self._parts.get(source)
        if old is not None and version <= old[0]:
            return
        expected = self.size[0] * self.size[1]
        if len(payload) > expected + 1024:
            return
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(payload, expected + 1)
            if len(raw) != expected or not decoder.eof or decoder.unused_data:
                return
        except zlib.error:
            return
        part = np.frombuffer(raw, dtype=np.int8).reshape(self.size[1], self.size[0]).copy()
        if np.any(np.abs(part.astype(np.int16)) > 8):
            return
        self._parts[source] = (version, part)
        self._packets[source] = (source, version, payload)
        self._version += 1
        self._snapshot = None

    def map_delta(self):
        if not self._packets:
            return None
        origins = sorted(self._packets)
        source = origins[self._relay_index % len(origins)]
        self._relay_index += 1
        return self._packets[source]

    def snapshot(self):
        if self._snapshot is not None:
            return self._snapshot
        evidence = np.zeros((self.size[1], self.size[0]), dtype=np.int16)
        seen = np.zeros(evidence.shape, dtype=bool)
        for _, part in self._parts.values():
            evidence += part
            seen |= part != 0
        walls = (evidence >= 3).astype(np.uint8)
        raw_blocked = pool(walls, self.RESOLUTION, np.max).astype(bool)
        known = pool(seen, self.RESOLUTION, np.max).astype(bool)
        blocked = ndimage.binary_dilation(raw_blocked, iterations=1)
        blocked[0, :] = blocked[-1, :] = True
        blocked[:, 0] = blocked[:, -1] = True
        # Keep fine wall mass for coverage; navigation inflation is excluded.
        weighted = walls.astype(np.float32)
        border = 12
        weighted[:border, :] *= .5
        weighted[-border:, :] *= .5
        weighted[border:-border, :border] *= .5
        weighted[border:-border, -border:] *= .5
        mass = pool(weighted, self.RESOLUTION, np.sum)
        for array in (walls, known, blocked, mass):
            array.flags.writeable = False
        self._snapshot = MapSnapshot(self._version, self.size, self.RESOLUTION,
                                     walls, known, blocked, mass)
        return self._snapshot

    def export_wall_grid(self):
        return self.snapshot().wall_grid.copy()

    def reject(self, goal, step):
        self._blacklist[self.snapshot().cell(goal.position)] = step + 240
        self._goal = None

    def next_goal(self, observation, navigator, peers):
        if observation.position is None:
            return None
        snapshot = self.snapshot()
        if self._goal is not None and observation.step - self._goal_step < 100:
            if np.linalg.norm(np.asarray(self._goal.position) - observation.position) > 24:
                return self._goal
        free = snapshot.known & ~snapshot.blocked
        frontier = free & ndimage.binary_dilation(~snapshot.known)
        labels, count = ndimage.label(frontier)
        field = navigator.distance_field(observation.position, snapshot)
        information = ndimage.uniform_filter((~snapshot.known).astype(float), size=11) * 121
        scored = []
        anchor = self.anchor or observation.position
        sector = 2 * math.pi * self.identifier / self.team_size
        for label in range(1, count + 1):
            cells = np.argwhere(labels == label)
            finite = np.isfinite(field[cells[:, 0], cells[:, 1]])
            cells = cells[finite]
            if not len(cells):
                continue
            # Representative: closest reachable point of this frontier cluster.
            costs = field[cells[:, 0], cells[:, 1]]
            r, c = map(int, cells[np.argmin(costs)])
            if self._blacklist.get((r, c), -1) > observation.step or field[r, c] < 30:
                continue
            point = snapshot.world((r, c))
            direction = math.atan2(point[1] - anchor[1], point[0] - anchor[0])
            score = information[r, c] - .06 * field[r, c] + 14 * math.cos(direction - sector)
            for peer in peers.values():
                if observation.step - peer.step > 120 or peer.goal is None:
                    continue
                if np.linalg.norm(np.asarray(peer.goal) - point) < 100:
                    score -= 50
            scored.append((score, (r, c), point))
        if not scored:
            self._goal = None
            return None
        _, _, point = max(scored, key=lambda x: (x[0], x[1]))
        self._goal = Goal(point, "explore")
        self._goal_step = observation.step
        return self._goal
