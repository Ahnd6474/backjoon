from __future__ import annotations

import sys

from solver.contracts import CirclePaper, PaperStack, TrianglePaper
from solver.evaluator import evaluate_visible_areas
from solver.search import search_board


def parse_input(text: str) -> PaperStack:
    tokens = text.split()
    if not tokens:
        return ()

    values = [int(token) for token in tokens]
    paper_count, cursor = values[0], 1
    papers = []
    for _ in range(paper_count):
        paper, cursor = _parse_paper(values, cursor)
        papers.append(paper)

    if cursor != len(values):
        raise ValueError("unexpected trailing input")
    return tuple(papers)


def _parse_paper(values: list[int], cursor: int) -> tuple[TrianglePaper | CirclePaper, int]:
    paper_type = values[cursor]
    cursor += 1
    if paper_type == 1:
        return _parse_triangle(values, cursor)
    if paper_type == 2:
        return _parse_circle(values, cursor)
    raise ValueError(f"unsupported paper type: {paper_type}")


def _parse_triangle(values: list[int], cursor: int) -> tuple[TrianglePaper, int]:
    x1, y1, x2, y2, x3, y3 = values[cursor : cursor + 6]
    return TrianglePaper(vertices=((x1, y1), (x2, y2), (x3, y3))), cursor + 6


def _parse_circle(values: list[int], cursor: int) -> tuple[CirclePaper, int]:
    x, y, radius = values[cursor : cursor + 3]
    return CirclePaper(center=(x, y), radius=radius), cursor + 3


def solve(text: str) -> str:
    papers = parse_input(text)
    rows = search_board(evaluate_visible_areas, papers)
    return format_rows(rows)


def format_rows(rows: tuple[tuple[float, ...], ...]) -> str:
    return "\n".join(" ".join(f"{area:.12f}" for area in row) for row in rows)


def main() -> None:
    sys.stdout.write(solve(sys.stdin.read()))


if __name__ == "__main__":
    main()
