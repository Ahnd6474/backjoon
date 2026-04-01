from __future__ import annotations

import math

import pytest

from solver.contracts import CirclePaper, PaperStack, TrianglePaper
from solver.evaluator import area_of_paper, evaluate_prefix_visible_areas, evaluate_visible_areas


def test_single_shapes_keep_their_full_area() -> None:
    triangle = TrianglePaper(vertices=((0, 0), (4, 0), (0, 3)))
    circle = CirclePaper(center=(8, -1), radius=2)

    visible = evaluate_visible_areas((triangle, circle))

    assert area_of_paper(triangle) == pytest.approx(6.0)
    assert visible == pytest.approx((6.0, 4.0 * math.pi), abs=1e-9, rel=1e-9)


def test_mixed_stack_matches_prompt_prefixes() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
    )

    visible_prefixes = evaluate_prefix_visible_areas(papers)

    assert len(visible_prefixes) == 2
    assert visible_prefixes[0] == pytest.approx((math.pi,), abs=1e-9, rel=1e-9)
    assert visible_prefixes[1] == pytest.approx((0.75 * math.pi, 2.0), abs=1e-9, rel=1e-9)


def test_multiple_top_circles_subtract_disjoint_covered_area_from_triangle() -> None:
    papers: PaperStack = (
        TrianglePaper(vertices=((0, 0), (10, 0), (0, 10))),
        CirclePaper(center=(2, 2), radius=1),
        CirclePaper(center=(6, 2), radius=1),
    )

    visible = evaluate_visible_areas(papers)

    assert visible == pytest.approx(
        (50.0 - (2.0 * math.pi), math.pi, math.pi),
        abs=1e-8,
        rel=1e-8,
    )


def test_identical_top_circle_fully_hides_bottom_circle() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=3),
        CirclePaper(center=(0, 0), radius=3),
    )

    visible = evaluate_visible_areas(papers)

    assert visible == pytest.approx((0.0, 9.0 * math.pi), abs=1e-9, rel=1e-9)


def test_tangent_shapes_do_not_create_false_overlap_area() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        TrianglePaper(vertices=((1, 0), (2, 0), (1, 1))),
    )

    visible = evaluate_visible_areas(papers)

    assert visible == pytest.approx((math.pi, 0.5), abs=1e-9, rel=1e-9)


def test_overlapping_top_circles_only_subtract_their_union_from_bottom_circle() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=3),
        CirclePaper(center=(-1, 0), radius=2),
        CirclePaper(center=(1, 0), radius=2),
    )

    overlap = (2.0 * (2.0**2) * math.acos(2.0 / 4.0)) - (2.0 * math.sqrt(4.0 - 1.0))
    expected_bottom = (9.0 * math.pi) - ((8.0 * math.pi) - overlap)
    expected_middle = (4.0 * math.pi) - overlap

    visible = evaluate_visible_areas(papers)

    assert visible == pytest.approx((expected_bottom, expected_middle, 4.0 * math.pi), abs=1e-8, rel=1e-8)


def test_precision_boundary_with_shared_triangle_edge_does_not_create_negative_area() -> None:
    papers: PaperStack = (
        TrianglePaper(vertices=((0, 0), (4, 0), (0, 4))),
        TrianglePaper(vertices=((4, 0), (5, 0), (4, 1))),
        CirclePaper(center=(6, 6), radius=1),
    )

    visible = evaluate_visible_areas(papers)

    assert visible == pytest.approx((8.0, 0.5, math.pi), abs=1e-9, rel=1e-9)


def test_large_mixed_stack_keeps_disjoint_occluders_exact() -> None:
    occluders = tuple(
        CirclePaper(center=(3 + (5 * index), 3), radius=1)
        for index in range(12)
    )
    papers: PaperStack = (
        TrianglePaper(vertices=((0, 0), (64, 0), (0, 64))),
        *occluders,
        TrianglePaper(vertices=((70, 0), (72, 0), (70, 2))),
    )

    visible = evaluate_visible_areas(papers)

    expected = (2048.0 - (12.0 * math.pi), *(math.pi for _ in occluders), 2.0)
    assert visible == pytest.approx(expected, abs=1e-8, rel=1e-8)
