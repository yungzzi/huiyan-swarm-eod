"""Two-phase red-team adapter: exploration -> synchronization -> placement."""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from swarm_rescue.simulation.drone.drone_abstract import DroneAbstract
from swarm_rescue.solutions.place_exploration import Explorer
from swarm_rescue.solutions.place_navigation import Navigator
from swarm_rescue.solutions.place_placement import BombPlanner
from swarm_rescue.solutions.place_types import Goal, Observation, PeerState


class MyDronePlace(DroneAbstract):
    # Replace these factories with teammate implementations of place_types contracts.
    explorer_factory = staticmethod(Explorer)
    navigator_factory = staticmethod(Navigator)
    planner_factory = staticmethod(BombPlanner)

    EXPLORE_FRACTION = .40
    SYNC_FRACTION = .54
    PLACE_DEADLINE_FRACTION = .90
    SUBMIT_FRACTION = .95

    def __init__(self, **kwargs):
        super().__init__(display_lidar_graph=False, **kwargs)
        n = self._misc_data.number_drones or 1
        self.explorer = self.explorer_factory(self.size_area, int(self.identifier), n)
        self.navigator = self.navigator_factory()
        self.planner = self.planner_factory(int(self.identifier), n)
        self.phase = "EXPLORE"
        self._peers = {}
        self._observation = None
        self._goal = None
        self._last_choose = -100
        self._zero_since = None
        self._initial_inventory = None
        self._exploration_submitted = False

    @staticmethod
    def _empty_command():
        return {"forward": 0.0, "lateral": 0.0, "rotation": 0.0,
                "grasper": 0, "place_bomb": 0}

    def _observe(self):
        gps, heading = self.measured_gps_position(), self.measured_compass_angle()
        position = (tuple(map(float, gps)) if gps is not None
                    and np.all(np.isfinite(gps)) else None)
        heading = float(heading) if heading is not None and math.isfinite(heading) else None
        velocity = self.measured_velocity()
        if velocity is None or not np.all(np.isfinite(velocity)):
            velocity = (0.0, 0.0)
        values = self.lidar_values()
        angles = np.asarray(self.lidar_rays_angles(), dtype=float)
        lidar = (np.asarray(values, dtype=float).copy() if values is not None
                 else np.full(angles.shape, np.nan))
        nonwalls, bombs = [], []
        for hit in self.semantic_values() or []:
            kind = getattr(getattr(hit, "entity_type", None), "name", None)
            angle, distance = float(hit.angle), float(hit.distance)
            if kind in {"BOMB", "DRONE", "DISPOSAL_CENTER", "OTHER"}:
                nonwalls.append((angle, distance))
            if kind == "BOMB" and math.isfinite(distance) and math.isfinite(angle):
                bombs.append((angle, distance))
        return Observation(int(self.elapsed_timestep), position, heading,
                           tuple(map(float, velocity)), lidar, angles,
                           int(self.carried_bombs_count()), tuple(nonwalls), tuple(bombs))

    def define_message_for_all(self):
        obs = self._observation
        if obs is None:
            return None
        own = PeerState(int(self.identifier), obs.step, obs.position, obs.inventory,
                        self.phase, self._goal.position if self._goal else None,
                        self.explorer.anchor)
        # Only received states/events/maps are forwarded, preserving their origins.
        states = tuple(self._peers.values()) + (own,)
        delta = self.explorer.map_delta() if obs.step % 12 == 0 else None
        return {"protocol": "place-v1", "states": states, "map": delta,
                "bombs": tuple(self.planner.events.values())}

    def _receive(self, observation):
        n = self._misc_data.number_drones or 1
        for _, packet in self.communicator.received_messages:
            if not isinstance(packet, dict) or packet.get("protocol") != "place-v1":
                continue
            for peer in packet.get("states", ()):
                if (not isinstance(peer, PeerState) or peer.identifier == self.identifier
                        or not 0 <= peer.identifier < n or peer.step > observation.step):
                    continue
                old = self._peers.get(peer.identifier)
                if old is None or peer.step > old.step:
                    self._peers[peer.identifier] = peer
            delta = packet.get("map")
            if isinstance(delta, tuple) and len(delta) == 3:
                self.explorer.ingest(*delta)
            self.planner.ingest(packet.get("bombs", ()))

    def _rendezvous_goal(self, source):
        leader = self._peers.get(0)
        anchor = leader.anchor if leader and leader.anchor else self.explorer.anchor
        if anchor is None:
            return None
        side = math.ceil(math.sqrt(self._misc_data.number_drones or 1))
        identifier = int(self.identifier)
        point = (anchor[0] + 40 * (identifier % side),
                 anchor[1] + 40 * (identifier // side))
        return Goal(point, source)

    def _limits(self):
        limit = self._misc_data.max_timestep_limit or 2000
        return tuple(int(limit * f) for f in
                     (self.EXPLORE_FRACTION, self.SYNC_FRACTION,
                      self.PLACE_DEADLINE_FRACTION, self.SUBMIT_FRACTION))

    def _should_submit(self, observation, hard_deadline):
        wall_limit = self._misc_data.max_walltime_limit
        if (observation.step >= hard_deadline
                or wall_limit and self.elapsed_walltime >= .92 * wall_limit):
            return not self.planner.pending
        n = self._misc_data.number_drones or 1
        all_zero = (self.phase == "PLACE" and observation.inventory == 0 and all(
            # Inventory cannot increase in this round; a confirmed zero
            # remains valid even if the reporting drone later leaves range.
            i in self._peers and self._peers[i].inventory == 0
            for i in range(n) if i != self.identifier))
        if all_zero and not self.planner.pending:
            if self._zero_since is None:
                self._zero_since = observation.step
            return observation.step - self._zero_since >= 24 + 3 * int(self.identifier)
        self._zero_since = None
        return False

    def control(self):
        observation = self._observe()
        self._observation = observation
        if self._initial_inventory is None:
            self._initial_inventory = observation.inventory
        self._receive(observation)
        confirmed = self.planner.confirm(observation)
        if confirmed is not None:
            print(f"[place-v1 #{self.identifier}] confirmed step={observation.step} "
                  f"inventory={observation.inventory}")
        explore_end, sync_end, place_deadline, submit_deadline = self._limits()
        phase = ("EXPLORE" if observation.step < explore_end else
                 "SYNC" if observation.step < sync_end else "PLACE")
        if phase != self.phase:
            self.phase = phase
            self._goal = None
            self.navigator.reset()
            print(f"[place-v1 #{self.identifier}] phase={phase} step={observation.step}")
        # Strategic mapping freezes after SYNC. Legal live sensors still control motion.
        if self.phase != "PLACE":
            self.explorer.update(observation)
        snapshot = self.explorer.snapshot()
        if self._should_submit(observation, submit_deadline):
            self.submit_exploration_map(self.explorer.export_wall_grid())
            self._exploration_submitted = True
            print(f"[place-v1 #{self.identifier}] submit step={observation.step} "
                  f"walls={int(snapshot.wall_grid.sum())} events={len(self.planner.events)}")
            return self._empty_command()

        if self.phase == "EXPLORE":
            if self._goal is None or observation.step - self._last_choose >= 40:
                self._goal = self.explorer.next_goal(observation, self.navigator, self._peers)
                self._last_choose = observation.step
        elif self.phase == "SYNC":
            self._goal = self._rendezvous_goal("sync")
        elif observation.inventory > 0:
            self._goal = self.planner.choose_goal(snapshot, observation, self.navigator,
                                                  self._peers, place_deadline)
        else:
            # Carry confirmed results back into contact with a potential submitter.
            self._goal = self._rendezvous_goal("report")

        command = self._empty_command()
        if (self.phase == "PLACE" and observation.inventory and self._goal is None
                and observation.step % 200 == 0 and observation.position is not None):
            cell = snapshot.cell(observation.position)
            print(f"[place-v1 #{self.identifier}] no placement goal step={observation.step} "
                  f"cell={cell} known={snapshot.known[cell]} blocked={snapshot.blocked[cell]}")
        if self._goal is None:
            return command
        result = self.navigator.step(self._goal, observation, snapshot)
        command.update(forward=result.forward, lateral=result.lateral, rotation=result.rotation)
        if result.status == "unreachable":
            if self.phase == "EXPLORE":
                self.explorer.reject(self._goal, observation.step)
            elif self.phase == "PLACE" and observation.inventory > 0:
                self.planner.reject(self._goal, observation.step)
            self._goal = None
            self.navigator.reset()
        elif self.phase == "EXPLORE" and result.status == "reached":
            self._goal = None
        elif self.phase == "PLACE" and observation.inventory > 0:
            if self.planner.request(result, observation):
                command["place_bomb"] = 1
        return command
