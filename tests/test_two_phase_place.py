"""Behavioral checks for communication, conservative navigation and placement."""
import math
import zlib

import numpy as np
import pytest

from swarm_rescue.simulation.utils.misc_data import MiscData
from swarm_rescue.solutions.my_drone_place import MyDronePlace
from swarm_rescue.solutions.place_exploration import Explorer
from swarm_rescue.solutions.place_navigation import Navigator
from swarm_rescue.solutions.place_placement import BombPlanner
from swarm_rescue.solutions.place_types import (
    BombEvent, Goal, MapSnapshot, NavResult, Observation,
)


def snapshot(known=None, blocked=None, mass=None):
    shape = (20, 20)
    known = np.ones(shape, dtype=bool) if known is None else known
    blocked = np.zeros(shape, dtype=bool) if blocked is None else blocked
    mass = np.ones(shape) if mass is None else mass
    return MapSnapshot(1, (320, 320), 16, np.zeros((320, 320), np.uint8),
                       known, blocked, mass)


def observation(step=1, inventory=2, position=(0., 0.)):
    return Observation(step, position, 0., (0., 0.), np.array([300.]),
                       np.array([0.]), inventory)


def test_duplicate_and_relayed_evidence_is_not_counted_again():
    receiver = Explorer((100, 100), 0, 3)
    part = np.zeros((100, 100), np.int8)
    part[50, 70] = 4
    payload = zlib.compress(part.tobytes())
    receiver.ingest(1, 10, payload)
    original = receiver.export_wall_grid()
    receiver.ingest(1, 10, payload)
    receiver.ingest(*receiver.map_delta())  # forwarding preserves original identity
    np.testing.assert_array_equal(receiver.export_wall_grid(), original)


def test_new_source_version_can_remove_an_old_wall():
    receiver = Explorer((100, 100), 0, 3)
    part = np.zeros((100, 100), np.int8)
    part[50, 70] = 4
    receiver.ingest(1, 10, zlib.compress(part.tobytes()))
    assert receiver.export_wall_grid()[50, 70]
    part[50, 70] = -4
    receiver.ingest(1, 11, zlib.compress(part.tobytes()))
    assert not receiver.export_wall_grid()[50, 70]
    part[50, 70] = 4
    receiver.ingest(1, 10, zlib.compress(part.tobytes()))  # stale cannot restore it
    assert not receiver.export_wall_grid()[50, 70]


def test_invalid_or_oversized_map_packets_are_ignored():
    receiver = Explorer((100, 100), 0, 2)
    for packet in (b"not zlib", zlib.compress(bytes(10001)), zlib.compress(bytes(9999))):
        receiver.ingest(1, 2, packet)
    assert receiver.export_wall_grid().sum() == 0
    assert not receiver._parts


def test_snapshot_arrays_cannot_be_changed_by_the_planner():
    explorer = Explorer((100, 100), 0, 1)
    explorer.update(observation(step=0))
    grid = explorer.snapshot()
    with pytest.raises(ValueError):
        grid.wall_grid[0, 0] = 1
    with pytest.raises(ValueError):
        grid.known[0, 0] = True


def test_navigation_does_not_cross_unknown_barrier():
    known = np.ones((20, 20), bool)
    known[:, 10] = False
    grid = snapshot(known=known)
    navigator = Navigator()
    assert math.isinf(navigator.estimate_cost(grid.world((10, 3)),
                                              grid.world((10, 16)), grid))


def test_diagonal_path_cannot_cut_between_walls():
    blocked = np.zeros((20, 20), bool)
    blocked[4, 5] = blocked[5, 4] = True
    known = np.zeros((20, 20), bool)
    known[4:6, 4:6] = True
    grid = snapshot(known, blocked)
    assert math.isinf(Navigator().estimate_cost(grid.world((4, 4)),
                                                grid.world((5, 5)), grid))


def test_navigation_routes_around_a_wall_and_rejects_outside_world():
    blocked = np.zeros((20, 20), bool)
    blocked[:15, 10] = True
    grid = snapshot(blocked=blocked)
    start, end = grid.world((8, 3)), grid.world((8, 16))
    navigator = Navigator()
    assert navigator.estimate_cost(start, end, grid) > np.linalg.norm(np.subtract(end, start))
    assert math.isinf(navigator.estimate_cost(start, (400., 0.), grid))


def test_only_inventory_change_confirms_a_bomb_and_request_has_reset_gap():
    planner = BombPlanner(0, 1)
    planner.goal = Goal((0., 0.), "place")
    assert planner.request(NavResult("reached"), observation(10, 2))
    assert not planner.request(NavResult("reached"), observation(10, 2))
    assert planner.confirm(observation(11, 2)) is None
    assert not planner.events
    planner.goal = Goal((0., 0.), "place")
    assert not planner.request(NavResult("reached"), observation(12, 2))
    assert planner.request(NavResult("reached"), observation(16, 2))
    event = planner.confirm(observation(17, 1))
    assert event is not None
    planner.ingest([event, event])
    assert len(planner.events) == 1


def test_wall_coverage_choice_moves_away_from_a_confirmed_bomb():
    mass = np.zeros((20, 20))
    mass[4, 4] = 100
    mass[15, 15] = 90
    grid = snapshot(mass=mass)
    planner = BombPlanner(0, 1)
    navigator = Navigator()
    obs = observation(position=grid.world((8, 8)))
    first = planner.choose_goal(grid, obs, navigator, {}, deadline=1000)
    planner.ingest([BombEvent(0, 1, first.position, 2)])
    planner.goal = None
    second = planner.choose_goal(grid, obs, navigator, {}, deadline=1000)
    assert np.linalg.norm(np.subtract(second.position, first.position)) >= 64
    assert grid.cell(first.position)[0] < 10
    assert grid.cell(second.position)[0] > 10


def test_bomb_returns_are_ignored_only_by_navigation_not_mapping():
    obs = Observation(1, (0., 0.), 0., (0., 0.), np.array([20.]),
                      np.array([0.]), 2, ((0., 20.),), ((0., 20.),))
    before = obs.lidar.copy()
    assert Navigator._avoid(np.array([.7, 0.]), obs)[0] == pytest.approx(.7)
    np.testing.assert_array_equal(obs.lidar, before)


def test_no_bomb_pulse_before_place_phase(monkeypatch):
    drone = MyDronePlace(identifier=0, misc_data=MiscData(
        size_area=(320, 320), number_drones=1, max_timestep_limit=2000,
        max_walltime_limit=90))
    monkeypatch.setattr(drone, "_observe", lambda: observation(799))
    monkeypatch.setattr(drone, "_receive", lambda obs: None)
    monkeypatch.setattr(drone.explorer, "next_goal", lambda *args: Goal((0., 0.), "explore"))
    monkeypatch.setattr(drone.navigator, "step", lambda *args: NavResult("reached"))
    assert drone.control()["place_bomb"] == 0
    monkeypatch.setattr(drone, "_observe", lambda: observation(801))
    assert drone.control()["place_bomb"] == 0
    assert drone.phase == "SYNC"
    monkeypatch.setattr(drone, "_observe", lambda: observation(1081))
    monkeypatch.setattr(drone.planner, "choose_goal", lambda *args: Goal((0., 0.), "place"))
    assert drone.control()["place_bomb"] == 1


def test_walltime_fallback_can_submit_while_still_exploring(monkeypatch):
    drone = MyDronePlace(identifier=0, misc_data=MiscData(
        size_area=(320, 320), number_drones=1, max_timestep_limit=2000,
        max_walltime_limit=90))
    drone.elapsed_walltime = 84
    monkeypatch.setattr(drone, "_observe", lambda: observation(100))
    monkeypatch.setattr(drone, "_receive", lambda obs: None)
    submitted = []
    monkeypatch.setattr(drone, "submit_exploration_map", lambda grid: submitted.append(grid))
    drone.control()
    assert len(submitted) == 1
    assert drone._exploration_submitted


def test_navigation_can_leave_only_inflation_not_an_actual_wall():
    blocked = np.zeros((20, 20), bool)
    blocked[8:11, 8:11] = True
    mass = np.zeros((20, 20))
    grid = snapshot(blocked=blocked, mass=mass)
    navigator = Navigator()
    assert np.isfinite(navigator.estimate_cost(grid.world((9, 9)), grid.world((15, 15)), grid))
    mass[8:11, 8:11] = 1
    grid = snapshot(blocked=blocked, mass=mass)
    assert math.isinf(Navigator().estimate_cost(grid.world((9, 9)), grid.world((15, 15)), grid))


def test_astar_also_preserves_unknown_barrier():
    known = np.ones((20, 20), bool)
    known[:, 10] = False
    grid = snapshot(known=known)
    assert not Navigator._astar((10, 3), (10, 16), grid)


def test_zero_inventory_is_monotonic_and_does_not_expire():
    from swarm_rescue.solutions.place_types import PeerState
    drone = MyDronePlace(identifier=0, misc_data=MiscData(
        size_area=(320, 320), number_drones=2, max_timestep_limit=2000,
        max_walltime_limit=90))
    drone.phase = "PLACE"
    drone._peers[1] = PeerState(1, 1100, (0., 0.), 0, "PLACE")
    assert not drone._should_submit(observation(1500, 0), 1900)
    assert drone._should_submit(observation(1524, 0), 1900)
    drone._peers[1] = PeerState(1, 1100, (0., 0.), 1, "PLACE")
    assert not drone._should_submit(observation(1525, 0), 1900)
