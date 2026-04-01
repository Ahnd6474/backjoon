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
    paper_count = values[0]
    cursor = 1
    papers = []
    for _ in range(paper_count):
        paper_type = values[cursor]
        cursor += 1
        if paper_type == 1:
            x1, y1, x2, y2, x3, y3 = values[cursor : cursor + 6]
            cursor += 6
            papers.append(
                TrianglePaper(vertices=((x1, y1), (x2, y2), (x3, y3)))
            )
            continue
        if paper_type == 2:
            x, y, radius = values[cursor : cursor + 3]
            cursor += 3
            papers.append(CirclePaper(center=(x, y), radius=radius))
            continue
        raise ValueError(f"unsupported paper type: {paper_type}")

    if cursor != len(values):
        raise ValueError("unexpected trailing input")
    return tuple(papers)


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
