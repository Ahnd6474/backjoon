from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, Iterator, TypeAlias

from solver.contracts import BOARD_COLUMNS, BOARD_ROWS, Board, BoardEvaluator, BoardRow, Digit, Score

Coordinate: TypeAlias = tuple[int, int]

ALL_DIGITS: Final[tuple[Digit, ...]] = tuple(range(10))
_PROMPT_SAMPLE: Final[tuple[str, ...]] = (
    "10203344536473",
    "01020102010201",
    "00000000008390",
    "00000000000400",
    "00000000000000",
    "55600000000089",
    "78900066000089",
    "00000789000077",
)


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Deterministic search settings for building and improving candidate boards."""

    improvement_passes: int = 2


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Scored board candidate returned by the local search pipeline."""

    board: Board
    score: Score
    evaluations: int
    source: str


@dataclass(slots=True)
class _SearchState:
    evaluator: BoardEvaluator
    best_board: Board | None = None
    best_score: Score | None = None
    evaluations: int = 0
    source: str = "uninitialized"

    def score(self, board: Board) -> Score:
        self.evaluations += 1
        return self.evaluator(board)

    def consider(self, board: Board, source: str) -> Score:
        score = self.score(board)
        if self.best_board is None or self.best_score is None:
            self.best_board = board
            self.best_score = score
            self.source = source
            return score

        if score > self.best_score or (score == self.best_score and board < self.best_board):
            self.best_board = board
            self.best_score = score
            self.source = source

        return score


def search_board(
    evaluator: BoardEvaluator,
    initial_board: Board | None = None,
    /,
) -> Board:
    """Return the highest-scoring board found by the deterministic search."""

    return search_board_with_result(evaluator, initial_board).board


def search_board_with_result(
    evaluator: BoardEvaluator,
    initial_board: Board | None = None,
    /,
    config: SearchConfig = SearchConfig(),
) -> SearchResult:
    """Search over fixed seeds and single-cell mutations while keeping evaluation isolated."""

    state = _SearchState(evaluator=evaluator)

    for label, board in _iter_seed_candidates(initial_board):
        seed_score = state.consider(board, f"{label}:seed")
        improved_board, improved_score = _improve_board(board, seed_score, state, config, label)
        if improved_board != board:
            state.consider(improved_board, f"{label}:improved")
        elif state.best_board is board:
            state.source = f"{label}:improved"

    assert state.best_board is not None
    assert state.best_score is not None
    return SearchResult(
        board=state.best_board,
        score=state.best_score,
        evaluations=state.evaluations,
        source=state.source,
    )


def _iter_seed_candidates(initial_board: Board | None) -> Iterator[tuple[str, Board]]:
    if initial_board is not None:
        yield "initial", _normalize_board(initial_board)

    yield "prompt-sample", _board_from_strings(_PROMPT_SAMPLE)
    yield "decimal-wave", _build_decimal_wave_board()
    yield "serpentine", _build_serpentine_board()
    yield "row-bands", _build_row_band_board()
    yield "diagonal-ridges", _build_diagonal_ridge_board()


def _build_decimal_wave_board() -> Board:
    return tuple(
        tuple((row * 3 + col * 7 + (row + col) // 2) % 10 for col in range(BOARD_COLUMNS))
        for row in range(BOARD_ROWS)
    )


def _build_serpentine_board() -> Board:
    rows: list[BoardRow] = []
    for row in range(BOARD_ROWS):
        values = [((row * BOARD_COLUMNS) + col) % 10 for col in range(BOARD_COLUMNS)]
        if row % 2 == 1:
            values.reverse()
        rows.append(tuple(values))
    return tuple(rows)


def _build_row_band_board() -> Board:
    return tuple(
        tuple((row + (col // 2)) % 10 for col in range(BOARD_COLUMNS))
        for row in range(BOARD_ROWS)
    )


def _build_diagonal_ridge_board() -> Board:
    return tuple(
        tuple((row * row + col + (row - col)) % 10 for col in range(BOARD_COLUMNS))
        for row in range(BOARD_ROWS)
    )


def _improve_board(
    board: Board,
    base_score: Score,
    state: _SearchState,
    config: SearchConfig,
    label: str,
) -> tuple[Board, Score]:
    current_board = board
    current_score = base_score

    for _ in range(config.improvement_passes):
        changed = False
        for row, col in _iter_scan_order():
            current_digit = current_board[row][col]
            best_digit = current_digit
            best_score = current_score

            for digit in _candidate_digits(current_board, row, col):
                if digit == current_digit:
                    continue

                trial_board = _with_digit(current_board, row, col, digit)
                trial_score = state.score(trial_board)
                if trial_score > best_score:
                    best_digit = digit
                    best_score = trial_score

            if best_digit != current_digit:
                current_board = _with_digit(current_board, row, col, best_digit)
                current_score = best_score
                state.consider(current_board, f"{label}:r{row}c{col}")
                changed = True

        if not changed:
            break

    return current_board, current_score


def _iter_scan_order() -> Iterable[Coordinate]:
    coordinates = [(row, col) for row in range(BOARD_ROWS) for col in range(BOARD_COLUMNS)]
    center_row = (BOARD_ROWS - 1) / 2
    center_col = (BOARD_COLUMNS - 1) / 2
    coordinates.sort(
        key=lambda item: (
            abs(item[0] - center_row) + abs(item[1] - center_col),
            item[0],
            item[1],
        )
    )
    return tuple(coordinates)


def _candidate_digits(board: Board, row: int, col: int) -> tuple[Digit, ...]:
    counts = [0] * len(ALL_DIGITS)
    for neighbor_row, neighbor_col in _iter_neighbor_coordinates(row, col):
        counts[board[neighbor_row][neighbor_col]] += 1

    prioritized = sorted(ALL_DIGITS, key=lambda digit: (-counts[digit], digit))
    rotation_start = (row * BOARD_COLUMNS + col) % len(ALL_DIGITS)
    rotated = [ALL_DIGITS[(rotation_start + offset) % len(ALL_DIGITS)] for offset in range(len(ALL_DIGITS))]

    ordered: list[Digit] = []
    for digit in (*prioritized, *rotated):
        if digit not in ordered:
            ordered.append(digit)
    return tuple(ordered)


def _iter_neighbor_coordinates(row: int, col: int) -> Iterator[Coordinate]:
    for row_delta in (-1, 0, 1):
        for col_delta in (-1, 0, 1):
            if row_delta == 0 and col_delta == 0:
                continue

            neighbor_row = row + row_delta
            neighbor_col = col + col_delta
            if 0 <= neighbor_row < BOARD_ROWS and 0 <= neighbor_col < BOARD_COLUMNS:
                yield neighbor_row, neighbor_col


def _with_digit(board: Board, row: int, col: int, digit: Digit) -> Board:
    rows = [list(board_row) for board_row in board]
    rows[row][col] = digit
    return tuple(tuple(board_row) for board_row in rows)


def _board_from_strings(lines: tuple[str, ...]) -> Board:
    return _normalize_board(tuple(tuple(int(char) for char in line) for line in lines))


def _normalize_board(board: Board) -> Board:
    if len(board) != BOARD_ROWS:
        raise ValueError(f"board must have {BOARD_ROWS} rows")

    normalized_rows: list[BoardRow] = []
    for row in board:
        if len(row) != BOARD_COLUMNS:
            raise ValueError(f"each board row must have {BOARD_COLUMNS} columns")
        normalized_row = tuple(_normalize_digit(value) for value in row)
        normalized_rows.append(normalized_row)

    return tuple(normalized_rows)


def _normalize_digit(value: int) -> Digit:
    if not 0 <= value <= 9:
        raise ValueError("board digits must be integers between 0 and 9")
    return int(value)


__all__ = [
    "SearchConfig",
    "SearchResult",
    "search_board",
    "search_board_with_result",
]
