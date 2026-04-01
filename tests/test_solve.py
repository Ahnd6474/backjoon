from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import solve
from solver.search import search_board_with_result


def test_committed_rows_match_deterministic_incremental_search() -> None:
    result = search_board_with_result(solve.sample_evaluator, solve.FINAL_PAPERS)

    assert result.rows == solve.FINAL_ROWS
    assert result.evaluations == solve.FINAL_EVALUATIONS
    assert result.source == solve.FINAL_SOURCE


def test_inspection_helper_returns_locked_result() -> None:
    result = solve.inspect_final_result()

    assert result.rows == solve.FINAL_ROWS
    assert result.evaluations == solve.FINAL_EVALUATIONS
    assert result.source == solve.FINAL_SOURCE


def test_solve_script_prints_only_the_locked_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(root / "solve.py")],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )

    assert completed.stderr == ""
    assert completed.stdout == f"{solve.format_rows(solve.FINAL_ROWS)}\n"
