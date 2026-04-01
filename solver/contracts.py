from __future__ import annotations

from typing import Final, Protocol, TypeAlias

BOARD_ROWS: Final[int] = 8
BOARD_COLUMNS: Final[int] = 14
BOARD_SHAPE: Final[tuple[int, int]] = (BOARD_ROWS, BOARD_COLUMNS)

Digit: TypeAlias = int
BoardRow: TypeAlias = tuple[Digit, ...]
Board: TypeAlias = tuple[BoardRow, ...]
Score: TypeAlias = int


class BoardEvaluator(Protocol):
    """Callable that scores a fully populated 8x14 digit board."""

    def __call__(self, board: Board, /) -> Score:
        ...


class BoardSearch(Protocol):
    """Callable that returns a candidate board using the shared evaluator."""

    def __call__(
        self,
        evaluator: BoardEvaluator,
        initial_board: Board | None = None,
        /,
    ) -> Board:
        ...
