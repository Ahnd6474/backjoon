from __future__ import annotations

import math

import pytest

from solver.contracts import CirclePaper, PaperStack, TrianglePaper
from solver.evaluator import evaluate_visible_areas
from solver.search import SearchResult, search_board, search_board_with_result


def test_search_board_evaluates_growing_prefixes_in_input_order() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
        CirclePaper(center=(3, 1), radius=2),
    )
    seen_prefixes: list[PaperStack] = []

    def evaluator(prefix: PaperStack) -> tuple[float, ...]:
        seen_prefixes.append(prefix)
        prefix_index = len(seen_prefixes)
        return tuple(float((prefix_index * 10) + offset) for offset in range(len(prefix)))

    rows = search_board(evaluator, papers)

    assert seen_prefixes == [
        papers[:1],
        papers[:2],
        papers[:3],
    ]
    assert rows == (
        (10.0,),
        (20.0, 21.0),
        (30.0, 31.0, 32.0),
    )


def test_search_board_with_result_tracks_rows_and_evaluation_count() -> None:
    papers: PaperStack = (
        TrianglePaper(vertices=((0, 0), (4, 0), (0, 4))),
        CirclePaper(center=(1, 1), radius=1),
    )

    def evaluator(prefix: PaperStack) -> tuple[int, ...]:
        return tuple(range(1, len(prefix) + 1))

    result = search_board_with_result(evaluator, papers)

    assert isinstance(result, SearchResult)
    assert result.rows == (
        (1.0,),
        (1.0, 2.0),
    )
    assert result.evaluations == 2
    assert result.source == "prefix-scan"


def test_search_board_uses_batch_prefix_evaluator_when_available() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
    )
    evaluator_calls = 0
    batch_calls = 0

    def evaluator(prefix: PaperStack) -> tuple[float, ...]:
        nonlocal evaluator_calls
        evaluator_calls += 1
        return tuple(float(index + 1) for index in range(len(prefix)))

    def evaluate_prefixes(prefixes: PaperStack) -> tuple[tuple[float, ...], ...]:
        nonlocal batch_calls
        batch_calls += 1
        assert prefixes == papers
        return (
            (1.0,),
            (1.0, 2.0),
        )

    evaluator.evaluate_prefixes = evaluate_prefixes  # type: ignore[attr-defined]

    result = search_board_with_result(evaluator, papers)

    assert result.rows == (
        (1.0,),
        (1.0, 2.0),
    )
    assert result.evaluations == 1
    assert result.source == "prefix-batch"
    assert evaluator_calls == 0
    assert batch_calls == 1


def test_search_board_uses_module_batch_prefix_evaluator_for_visible_area_solver() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=2),
        TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
        CirclePaper(center=(1, 0), radius=1),
    )

    result = search_board_with_result(evaluate_visible_areas, papers)

    assert result.rows[0] == pytest.approx((4.0 * math.pi,), abs=1e-9, rel=1e-9)
    assert result.rows[1] == pytest.approx(((4.0 * math.pi) - 2.0, 2.0), abs=1e-9, rel=1e-9)
    assert result.rows[2] == pytest.approx(
        (8.71017612387708, 0.7146018366025526, math.pi),
        abs=1e-9,
        rel=1e-9,
    )
    assert result.evaluations == 1
    assert result.source == "prefix-batch"


def test_search_board_rejects_batch_results_that_do_not_match_prefix_count() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        CirclePaper(center=(1, 1), radius=1),
    )

    def evaluator(prefix: PaperStack) -> tuple[float, ...]:
        return tuple(float(index) for index in range(len(prefix)))

    def evaluate_prefixes(prefixes: PaperStack) -> tuple[tuple[float, ...], ...]:
        assert prefixes == papers
        return ((1.0,),)

    evaluator.evaluate_prefixes = evaluate_prefixes  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="expected 2, received 1"):
        search_board_with_result(evaluator, papers)


def test_search_board_rejects_evaluator_results_that_do_not_match_prefix_size() -> None:
    papers: PaperStack = (
        CirclePaper(center=(0, 0), radius=1),
        CirclePaper(center=(1, 1), radius=1),
    )

    def evaluator(prefix: PaperStack) -> tuple[float, ...]:
        return (42.0,)

    with pytest.raises(ValueError, match="expected 2, received 1"):
        search_board(evaluator, papers)
