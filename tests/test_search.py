from __future__ import annotations

from solver.contracts import BOARD_COLUMNS, BOARD_ROWS, Board
from solver.search import SearchResult, search_board, search_board_with_result


def test_search_board_is_deterministic_and_returns_a_valid_digit_grid() -> None:
    def evaluator(board: Board) -> int:
        return sum(sum(row) for row in board)

    first = search_board(evaluator)
    second = search_board(evaluator)

    assert first == second
    assert len(first) == BOARD_ROWS
    assert all(len(row) == BOARD_COLUMNS for row in first)
    assert all(0 <= digit <= 9 for row in first for digit in row)
    assert first == tuple(tuple(9 for _ in range(BOARD_COLUMNS)) for _ in range(BOARD_ROWS))


def test_search_board_with_result_tracks_score_and_improves_from_initial_board() -> None:
    target_digit = 7
    initial_board = tuple(tuple(0 for _ in range(BOARD_COLUMNS)) for _ in range(BOARD_ROWS))

    def evaluator(board: Board) -> int:
        return sum(digit == target_digit for row in board for digit in row)

    result = search_board_with_result(evaluator, initial_board)

    assert isinstance(result, SearchResult)
    assert result.board == tuple(
        tuple(target_digit for _ in range(BOARD_COLUMNS)) for _ in range(BOARD_ROWS)
    )
    assert result.score == BOARD_ROWS * BOARD_COLUMNS
    assert result.evaluations > 0
    assert result.source
