import inspect
from typing import get_type_hints

import solver
from solver import contracts


def test_solver_contract_exports_are_stable() -> None:
    assert solver.BOARD_ROWS == 8
    assert solver.BOARD_COLUMNS == 14
    assert solver.BOARD_SHAPE == (solver.BOARD_ROWS, solver.BOARD_COLUMNS)
    assert solver.__all__ == [
        "BOARD_COLUMNS",
        "BOARD_ROWS",
        "BOARD_SHAPE",
        "Board",
        "BoardEvaluator",
        "BoardRow",
        "BoardSearch",
        "Digit",
        "Score",
    ]


def test_callable_protocol_signatures_match_the_contract() -> None:
    evaluator_signature = inspect.signature(contracts.BoardEvaluator.__call__)
    search_signature = inspect.signature(contracts.BoardSearch.__call__)
    evaluator_hints = get_type_hints(contracts.BoardEvaluator.__call__)
    search_hints = get_type_hints(contracts.BoardSearch.__call__)

    assert list(evaluator_signature.parameters) == ["self", "board"]
    assert evaluator_hints["board"] == contracts.Board
    assert evaluator_hints["return"] is contracts.Score

    assert list(search_signature.parameters) == ["self", "evaluator", "initial_board"]
    assert search_signature.parameters["initial_board"].default is None
    assert search_hints["evaluator"] == contracts.BoardEvaluator
    assert search_hints["initial_board"] == contracts.Board | None
    assert search_hints["return"] == contracts.Board
