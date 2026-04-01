from __future__ import annotations

from solver.contracts import Board
from solver.evaluator import score_board
from solver.search import SearchResult, search_board_with_result

FINAL_BOARD: Board = (
    (0, 1, 2, 6, 4, 5, 6, 1, 8, 9, 0, 1, 2, 3),
    (3, 6, 1, 4, 3, 0, 1, 2, 9, 8, 7, 4, 5, 4),
    (0, 9, 4, 1, 2, 3, 8, 5, 7, 1, 8, 9, 0, 1),
    (5, 4, 3, 2, 1, 6, 6, 7, 1, 6, 5, 3, 3, 2),
    (6, 7, 8, 9, 0, 1, 4, 9, 4, 5, 9, 7, 1, 2),
    (3, 1, 4, 0, 9, 8, 7, 2, 5, 7, 0, 3, 7, 0),
    (4, 1, 5, 6, 8, 9, 2, 0, 2, 3, 0, 1, 6, 7),
    (1, 0, 1, 8, 7, 6, 1, 1, 3, 5, 1, 0, 2, 8),
)
FINAL_SCORE = 1906
FINAL_SOURCE = "serpentine:r1c0"


def format_board(board: Board) -> str:
    return "\n".join("".join(str(digit) for digit in row) for row in board)


def inspect_final_result() -> SearchResult:
    """Re-run the deterministic search and verify the committed board stays in sync."""

    result = search_board_with_result(score_board)
    if result.board != FINAL_BOARD:
        raise RuntimeError("committed board is out of sync with solver.search")
    if result.score != FINAL_SCORE:
        raise RuntimeError("committed score is out of sync with solver.evaluator")
    if result.source != FINAL_SOURCE:
        raise RuntimeError("committed search source is out of sync with solver.search")
    return result


def main() -> None:
    print(format_board(FINAL_BOARD))


if __name__ == "__main__":
    main()
