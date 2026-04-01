from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import solve
from solver.evaluator import score_board
from solver.search import search_board_with_result


def test_committed_board_matches_deterministic_search() -> None:
    result = search_board_with_result(score_board)

    assert result.board == solve.FINAL_BOARD
    assert result.score == solve.FINAL_SCORE
    assert result.source == solve.FINAL_SOURCE


def test_inspection_helper_returns_locked_result() -> None:
    result = solve.inspect_final_result()

    assert result.board == solve.FINAL_BOARD
    assert result.score == solve.FINAL_SCORE
    assert result.source == solve.FINAL_SOURCE


def test_solve_script_prints_only_the_digit_grid() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(root / "solve.py")],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )

    assert completed.stderr == ""
    assert completed.stdout == f"{solve.format_board(solve.FINAL_BOARD)}\n"
