"""Small sensor scenarios for the red team's submitted wall map."""

import math

import numpy as np

from swarm_rescue.solutions.place_mapping import WallEvidenceMap


def test_repeated_wall_returns_create_a_wall_and_mark_ray_free():
    wall_map = WallEvidenceMap((100, 100))
    for _ in range(2):
        wall_map.update((0, 0), 0.0, (20.0,), (0.0,))

    submitted = wall_map.binary_wall_grid()
    assert submitted.shape == (100, 100)
    assert submitted.dtype == np.uint8
    assert submitted[50, 70] == 1  # world (20, 0)
    assert wall_map.evidence[50, 55] < 0  # free space on the ray
    assert submitted[50, 55] == 0


def test_world_y_is_flipped_in_the_submitted_grid():
    wall_map = WallEvidenceMap((100, 100))
    for _ in range(2):
        wall_map.update((0, 0), math.pi / 2, (20.0,), (0.0,))

    assert wall_map.binary_wall_grid()[30, 50] == 1  # world (0, +20)
    assert wall_map.binary_wall_grid()[70, 50] == 0


def test_no_return_or_semantically_identified_bomb_does_not_become_wall():
    wall_map = WallEvidenceMap((100, 100))
    for _ in range(2):
        wall_map.update((0, 0), 0.0, (20.0,), (0.0,), [(0.0, 20.0)])
        wall_map.update((0, 0), 0.0, (300.0,), (math.pi / 2,))

    assert wall_map.binary_wall_grid().sum() == 0


def test_later_free_readings_can_correct_an_earlier_wall():
    wall_map = WallEvidenceMap((100, 100))
    for _ in range(2):
        wall_map.update((0, 0), 0.0, (20.0,), (0.0,))
    assert wall_map.binary_wall_grid()[50, 70] == 1

    for _ in range(2):
        wall_map.update((0, 0), 0.0, (300.0,), (0.0,))
    assert wall_map.binary_wall_grid()[50, 70] == 0
