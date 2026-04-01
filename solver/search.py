from __future__ import annotations

from dataclasses import dataclass

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

    rows = tuple(_evaluate_prefix(evaluator, papers, prefix_length) for prefix_length in range(1, len(papers) + 1))
    return SearchResult(rows=rows, evaluations=len(rows))


def _evaluate_prefix(
    evaluator: VisibleAreaEvaluator,
    papers: PaperStack,
    prefix_length: int,
) -> VisibleAreas:
    prefix = papers[:prefix_length]
    return _normalize_visible_areas(evaluator(prefix), expected_size=prefix_length)


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
