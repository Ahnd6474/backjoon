from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Callable

from solver.contracts import IncrementalVisibleAreas, PaperStack, VisibleAreaEvaluator, VisibleAreas


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Incremental execution result returned by the search compatibility wrapper."""

    rows: IncrementalVisibleAreas
    evaluations: int
    source: str = "prefix-scan"


def search_board(
    evaluator: VisibleAreaEvaluator,
    papers: PaperStack,
    /,
) -> IncrementalVisibleAreas:
    """Evaluate each 1..i paper prefix and return the visible-area rows in order."""

    return search_board_with_result(evaluator, papers).rows


def search_board_with_result(
    evaluator: VisibleAreaEvaluator,
    papers: PaperStack,
    /,
) -> SearchResult:
    """Run the evaluator over every prefix while preserving stable output ordering."""

    incremental_evaluator = _resolve_incremental_evaluator(evaluator)
    if incremental_evaluator is not None:
        rows = _normalize_incremental_visible_areas(incremental_evaluator(papers), expected_prefix_count=len(papers))
        return SearchResult(rows=rows, evaluations=1 if rows else 0, source="prefix-batch")

    rows = tuple(_evaluate_prefix(evaluator, papers, prefix_length) for prefix_length in range(1, len(papers) + 1))
    return SearchResult(rows=rows, evaluations=len(rows))


def _evaluate_prefix(
    evaluator: VisibleAreaEvaluator,
    papers: PaperStack,
    prefix_length: int,
) -> VisibleAreas:
    prefix = papers[:prefix_length]
    return _normalize_visible_areas(evaluator(prefix), expected_size=prefix_length)


def _resolve_incremental_evaluator(
    evaluator: VisibleAreaEvaluator,
) -> Callable[[PaperStack], IncrementalVisibleAreas] | None:
    direct = getattr(evaluator, "evaluate_prefixes", None)
    if callable(direct):
        return direct

    module_name = getattr(evaluator, "__module__", None)
    if not isinstance(module_name, str):
        return None

    module = _import_evaluator_module(module_name)
    if module is None:
        return None

    module_evaluator = getattr(module, getattr(evaluator, "__name__", ""), None)
    if module_evaluator is evaluator:
        incremental = getattr(module, "evaluate_prefix_visible_areas", None)
        if callable(incremental):
            return incremental
    return None


def _import_evaluator_module(module_name: str) -> ModuleType | None:
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        return None


def _normalize_incremental_visible_areas(
    rows: IncrementalVisibleAreas,
    *,
    expected_prefix_count: int,
) -> IncrementalVisibleAreas:
    normalized_rows = tuple(
        _normalize_visible_areas(row, expected_size=prefix_length)
        for prefix_length, row in enumerate(rows, start=1)
    )
    if len(normalized_rows) != expected_prefix_count:
        raise ValueError(
            "incremental evaluator must return one visible-area row per input prefix; "
            f"expected {expected_prefix_count}, received {len(normalized_rows)}"
        )
    return normalized_rows


def _normalize_visible_areas(visible_areas: VisibleAreas, *, expected_size: int) -> VisibleAreas:
    normalized = tuple(float(area) for area in visible_areas)
    if len(normalized) != expected_size:
        raise ValueError(
            "evaluator must return one visible area per paper in the current prefix; "
            f"expected {expected_size}, received {len(normalized)}"
        )
    return normalized


__all__ = [
    "SearchResult",
    "search_board",
    "search_board_with_result",
]
