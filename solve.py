from __future__ import annotations

from solver.contracts import CirclePaper, IncrementalVisibleAreas, PaperStack, TrianglePaper, VisibleAreas
from solver.search import SearchResult, search_board_with_result

FINAL_PAPERS: PaperStack = (
    CirclePaper(center=(0, 0), radius=1),
    TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
    CirclePaper(center=(3, 1), radius=2),
)
FINAL_ROWS: IncrementalVisibleAreas = (
    (10.0,),
    (20.0, 21.0),
    (30.0, 31.0, 32.0),
)
FINAL_EVALUATIONS = 3
FINAL_SOURCE = "prefix-scan"


def sample_evaluator(papers: PaperStack, /) -> VisibleAreas:
    """Deterministic evaluator used to lock the incremental search integration."""

    prefix_index = len(papers)
    return tuple(float((prefix_index * 10) + offset) for offset in range(prefix_index))


def format_rows(rows: IncrementalVisibleAreas) -> str:
    return "\n".join(" ".join(f"{area:.12f}" for area in row) for row in rows)


def inspect_final_result() -> SearchResult:
    """Re-run the incremental pipeline and verify the locked sample output stays in sync."""

    result = search_board_with_result(sample_evaluator, FINAL_PAPERS)
    if result.rows != FINAL_ROWS:
        raise RuntimeError("committed rows are out of sync with solver.search")
    if result.evaluations != FINAL_EVALUATIONS:
        raise RuntimeError("committed evaluation count is out of sync with solver.search")
    if result.source != FINAL_SOURCE:
        raise RuntimeError("committed search source is out of sync with solver.search")
    return result


def main() -> None:
    print(format_rows(FINAL_ROWS))


if __name__ == "__main__":
    main()
