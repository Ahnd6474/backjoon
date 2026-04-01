from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from solver.contracts import BOARD_COLUMNS, BOARD_ROWS, Board, Score

Position: TypeAlias = tuple[int, int]
TraceReason: TypeAlias = Literal["complete", "digit_absent", "digit_unreachable"]

_NEIGHBOR_DELTAS: Final[tuple[tuple[int, int], ...]] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


@dataclass(frozen=True)
class NumberTrace:
    """Explains whether a single decimal number is readable on the board."""

    number: int
    digits: str
    readable: bool
    reason: TraceReason
    failing_index: int | None
    required_digit: int | None
    matched_prefix_length: int
    frontier: tuple[Position, ...]
    candidate_positions: tuple[Position, ...]


@dataclass(frozen=True)
class BoardEvaluation:
    """Summarizes the score and the first unreadable number."""

    max_prefix: Score
    first_missing: int
    witness: NumberTrace


class _CompiledBoard:
    def __init__(self, board: Board) -> None:
        if len(board) != BOARD_ROWS:
            raise ValueError(
                f"board must have exactly {BOARD_ROWS} rows; received {len(board)}"
            )

        digit_masks = [0] * 10
        positions: list[Position] = []

        for row_index, row in enumerate(board):
            if len(row) != BOARD_COLUMNS:
                raise ValueError(
                    f"row {row_index} must have exactly {BOARD_COLUMNS} columns; "
                    f"received {len(row)}"
                )

            for column_index, digit in enumerate(row):
                if not isinstance(digit, int) or not 0 <= digit <= 9:
                    raise ValueError(
                        "board entries must be integers between 0 and 9; "
                        f"received {digit!r} at {(row_index, column_index)}"
                    )

                cell_index = (row_index * BOARD_COLUMNS) + column_index
                digit_masks[digit] |= 1 << cell_index
                positions.append((row_index, column_index))

        neighbor_masks = [0] * len(positions)
        for cell_index, (row_index, column_index) in enumerate(positions):
            mask = 0
            for row_delta, column_delta in _NEIGHBOR_DELTAS:
                next_row = row_index + row_delta
                next_column = column_index + column_delta
                if not (0 <= next_row < BOARD_ROWS and 0 <= next_column < BOARD_COLUMNS):
                    continue
                neighbor_index = (next_row * BOARD_COLUMNS) + next_column
                mask |= 1 << neighbor_index
            neighbor_masks[cell_index] = mask

        self._digit_masks = tuple(digit_masks)
        self._positions = tuple(positions)
        self._neighbor_masks = tuple(neighbor_masks)

    def trace_number(self, number: int) -> NumberTrace:
        if number < 0:
            raise ValueError(f"number must be non-negative; received {number}")

        digits = str(number)
        current_mask = self._digit_masks[int(digits[0])]
        if current_mask == 0:
            return NumberTrace(
                number=number,
                digits=digits,
                readable=False,
                reason="digit_absent",
                failing_index=0,
                required_digit=int(digits[0]),
                matched_prefix_length=0,
                frontier=(),
                candidate_positions=(),
            )

        for digit_index, digit_char in enumerate(digits[1:], start=1):
            required_digit = int(digit_char)
            candidate_mask = self._digit_masks[required_digit]
            if candidate_mask == 0:
                return NumberTrace(
                    number=number,
                    digits=digits,
                    readable=False,
                    reason="digit_absent",
                    failing_index=digit_index,
                    required_digit=required_digit,
                    matched_prefix_length=digit_index,
                    frontier=self._positions_from_mask(current_mask),
                    candidate_positions=(),
                )

            next_mask = self._advance(current_mask) & candidate_mask
            if next_mask == 0:
                return NumberTrace(
                    number=number,
                    digits=digits,
                    readable=False,
                    reason="digit_unreachable",
                    failing_index=digit_index,
                    required_digit=required_digit,
                    matched_prefix_length=digit_index,
                    frontier=self._positions_from_mask(current_mask),
                    candidate_positions=self._positions_from_mask(candidate_mask),
                )

            current_mask = next_mask

        return NumberTrace(
            number=number,
            digits=digits,
            readable=True,
            reason="complete",
            failing_index=None,
            required_digit=None,
            matched_prefix_length=len(digits),
            frontier=self._positions_from_mask(current_mask),
            candidate_positions=(),
        )

    def _advance(self, current_mask: int) -> int:
        next_mask = 0
        remaining_mask = current_mask
        while remaining_mask:
            least_significant_bit = remaining_mask & -remaining_mask
            cell_index = least_significant_bit.bit_length() - 1
            next_mask |= self._neighbor_masks[cell_index]
            remaining_mask ^= least_significant_bit
        return next_mask

    def _positions_from_mask(self, mask: int) -> tuple[Position, ...]:
        ordered_positions: list[Position] = []
        remaining_mask = mask
        while remaining_mask:
            least_significant_bit = remaining_mask & -remaining_mask
            cell_index = least_significant_bit.bit_length() - 1
            ordered_positions.append(self._positions[cell_index])
            remaining_mask ^= least_significant_bit
        return tuple(ordered_positions)


def trace_number(board: Board, number: int, /) -> NumberTrace:
    """Evaluate one number against a candidate board."""

    return _CompiledBoard(board).trace_number(number)


def evaluate_board(board: Board, /) -> BoardEvaluation:
    """Return the largest X for which every number from 1 through X is readable."""

    compiled_board = _CompiledBoard(board)
    number = 1
    while True:
        witness = compiled_board.trace_number(number)
        if not witness.readable:
            return BoardEvaluation(
                max_prefix=number - 1,
                first_missing=number,
                witness=witness,
            )
        number += 1


def score_board(board: Board, /) -> Score:
    """Compatibility scorer matching the frozen evaluator contract."""

    return evaluate_board(board).max_prefix


__all__ = [
    "BoardEvaluation",
    "NumberTrace",
    "Position",
    "TraceReason",
    "evaluate_board",
    "score_board",
    "trace_number",
]
