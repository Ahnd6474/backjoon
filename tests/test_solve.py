from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import solve
from solver.contracts import CirclePaper, TrianglePaper


PROMPT_SAMPLE_INPUT = """\
2
2 0 0 1
1 0 0 2 0 0 2
"""

PROMPT_SAMPLE_OUTPUT = """\
3.141592653590
2.356194490192 2.000000000000"""


def test_parse_input_builds_mixed_paper_stack() -> None:
    papers = solve.parse_input(PROMPT_SAMPLE_INPUT)

    assert papers == (
        CirclePaper(center=(0, 0), radius=1),
        TrianglePaper(vertices=((0, 0), (2, 0), (0, 2))),
    )


def test_solve_matches_prompt_sample_output() -> None:
    assert solve.solve(PROMPT_SAMPLE_INPUT) == PROMPT_SAMPLE_OUTPUT


def test_solve_formats_empty_rows_as_empty_output() -> None:
    assert solve.format_rows(()) == ""


def test_solve_script_reads_stdin_and_prints_rows_only() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(root / "solve.py")],
        input=PROMPT_SAMPLE_INPUT,
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )

    assert completed.stderr == ""
    assert completed.stdout == PROMPT_SAMPLE_OUTPUT


def test_parse_input_rejects_unknown_paper_type() -> None:
    with pytest.raises(ValueError, match="unsupported paper type"):
        solve.parse_input("1\n3 0 0 0\n")
