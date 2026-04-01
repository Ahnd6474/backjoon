from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from solver.contracts import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    Board,
    CirclePaper,
    Paper,
    PaperStack,
    Score,
    TrianglePaper,
    VisibleAreas,
)

Position: TypeAlias = tuple[int, int]
TraceReason: TypeAlias = Literal["complete", "digit_absent", "digit_unreachable"]
VerticalInterval: TypeAlias = tuple[float, float]

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
_EPS: Final[float] = 1e-12
_AREA_TOLERANCE: Final[float] = 1e-12
_MAX_INTEGRATION_DEPTH: Final[int] = 30


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


def area_of_paper(paper: Paper, /) -> float:
    """Return the exact area of one paper before any occlusion."""

    if isinstance(paper, CirclePaper):
        return math.pi * paper.radius * paper.radius

    (x1, y1), (x2, y2), (x3, y3) = paper.vertices
    return abs(
        (x1 * (y2 - y3))
        + (x2 * (y3 - y1))
        + (x3 * (y1 - y2))
    ) / 2.0


def evaluate_visible_areas(papers: PaperStack, /) -> VisibleAreas:
    """Return the visible area for each paper in the current stack."""

    visible_areas: list[float] = []
    for index, paper in enumerate(papers):
        visible_area = _visible_area_against_occluders(paper, papers[index + 1 :])
        visible_areas.append(max(0.0, visible_area))
    return tuple(visible_areas)


def evaluate_prefix_visible_areas(papers: PaperStack, /) -> tuple[VisibleAreas, ...]:
    """Evaluate the visible-area vector after each prefix of the stack."""

    return tuple(evaluate_visible_areas(papers[: index + 1]) for index in range(len(papers)))


def _visible_area_against_occluders(target: Paper, occluders: PaperStack) -> float:
    xmin, xmax = _x_bounds(target)
    if xmax - xmin <= _EPS:
        return 0.0

    relevant_occluders = tuple(
        occluder
        for occluder in occluders
        if _x_bounds(occluder)[0] <= xmax + _EPS and _x_bounds(occluder)[1] >= xmin - _EPS
    )
    breakpoints = _integration_breakpoints(target, relevant_occluders)
    visible_area = 0.0
    for left, right in zip(breakpoints, breakpoints[1:]):
        if right - left <= _EPS:
            continue
        visible_area += _adaptive_simpson(
            lambda x: _visible_length_at_x(target, relevant_occluders, x),
            left,
            right,
            _AREA_TOLERANCE,
            _MAX_INTEGRATION_DEPTH,
        )
    return visible_area


def _visible_length_at_x(target: Paper, occluders: PaperStack, x: float) -> float:
    target_interval = _vertical_interval(target, x)
    if target_interval is None:
        return 0.0

    covered_intervals: list[VerticalInterval] = []
    for occluder in occluders:
        occluder_interval = _vertical_interval(occluder, x)
        if occluder_interval is None:
            continue
        overlap = _intersect_intervals(target_interval, occluder_interval)
        if overlap is not None:
            covered_intervals.append(overlap)

    visible_length = (target_interval[1] - target_interval[0]) - _union_length(covered_intervals)
    if abs(visible_length) <= _AREA_TOLERANCE:
        return 0.0
    return max(0.0, visible_length)


def _integration_breakpoints(target: Paper, occluders: PaperStack) -> tuple[float, ...]:
    xmin, xmax = _x_bounds(target)
    points = {xmin, xmax}
    for paper in (target, *occluders):
        for point in _shape_x_breakpoints(paper):
            if xmin + _EPS < point < xmax - _EPS:
                points.add(point)
    return tuple(sorted(points))


def _shape_x_breakpoints(paper: Paper) -> tuple[float, ...]:
    if isinstance(paper, CirclePaper):
        center_x, _ = paper.center
        return (center_x - paper.radius, center_x + paper.radius)
    return tuple(float(vertex[0]) for vertex in paper.vertices)


def _x_bounds(paper: Paper) -> tuple[float, float]:
    if isinstance(paper, CirclePaper):
        center_x, _ = paper.center
        return center_x - paper.radius, center_x + paper.radius

    xs = [vertex[0] for vertex in paper.vertices]
    return float(min(xs)), float(max(xs))


def _vertical_interval(paper: Paper, x: float) -> VerticalInterval | None:
    if isinstance(paper, CirclePaper):
        center_x, center_y = paper.center
        dx = x - center_x
        radius_sq = paper.radius * paper.radius
        inside = radius_sq - (dx * dx)
        if inside < -_EPS:
            return None
        dy = math.sqrt(max(0.0, inside))
        return center_y - dy, center_y + dy

    intersections = _triangle_intersections_at_x(paper, x)
    if not intersections:
        return None
    return min(intersections), max(intersections)


def _triangle_intersections_at_x(paper: TrianglePaper, x: float) -> list[float]:
    intersections: list[float] = []
    vertices = paper.vertices
    for start, end in zip(vertices, (*vertices[1:], vertices[0])):
        edge_intersections = _edge_intersections_at_x(start, end, x)
        if edge_intersections:
            intersections.extend(edge_intersections)
    return intersections


def _edge_intersections_at_x(start: Position, end: Position, x: float) -> tuple[float, ...]:
    x1, y1 = start
    x2, y2 = end
    if abs(x1 - x2) <= _EPS:
        if abs(x - x1) <= _EPS:
            return float(y1), float(y2)
        return ()

    lower_x = min(x1, x2)
    upper_x = max(x1, x2)
    if x < lower_x - _EPS or x > upper_x + _EPS:
        return ()

    t = (x - x1) / (x2 - x1)
    if -_EPS <= t <= 1 + _EPS:
        return (y1 + (t * (y2 - y1)),)
    return ()


def _intersect_intervals(
    left: VerticalInterval,
    right: VerticalInterval,
) -> VerticalInterval | None:
    lower = max(left[0], right[0])
    upper = min(left[1], right[1])
    if upper - lower <= _EPS:
        return None
    return lower, upper


def _union_length(intervals: list[VerticalInterval]) -> float:
    if not intervals:
        return 0.0

    intervals.sort()
    total = 0.0
    current_lower, current_upper = intervals[0]
    for lower, upper in intervals[1:]:
        if lower > current_upper + _EPS:
            total += current_upper - current_lower
            current_lower, current_upper = lower, upper
            continue
        current_upper = max(current_upper, upper)

    total += current_upper - current_lower
    return total


def _adaptive_simpson(
    function,
    left: float,
    right: float,
    tolerance: float,
    depth: int,
) -> float:
    midpoint = (left + right) / 2.0
    f_left = function(left)
    f_mid = function(midpoint)
    f_right = function(right)
    whole = _simpson(left, right, f_left, f_mid, f_right)
    return _adaptive_simpson_recursive(
        function,
        left,
        midpoint,
        right,
        f_left,
        f_mid,
        f_right,
        whole,
        tolerance,
        depth,
    )


def _adaptive_simpson_recursive(
    function,
    left: float,
    midpoint: float,
    right: float,
    f_left: float,
    f_mid: float,
    f_right: float,
    whole: float,
    tolerance: float,
    depth: int,
) -> float:
    left_mid = (left + midpoint) / 2.0
    right_mid = (midpoint + right) / 2.0
    f_left_mid = function(left_mid)
    f_right_mid = function(right_mid)

    left_area = _simpson(left, midpoint, f_left, f_left_mid, f_mid)
    right_area = _simpson(midpoint, right, f_mid, f_right_mid, f_right)
    delta = left_area + right_area - whole

    if depth <= 0 or abs(delta) <= 15.0 * tolerance:
        return left_area + right_area + (delta / 15.0)

    return _adaptive_simpson_recursive(
        function,
        left,
        left_mid,
        midpoint,
        f_left,
        f_left_mid,
        f_mid,
        left_area,
        tolerance / 2.0,
        depth - 1,
    ) + _adaptive_simpson_recursive(
        function,
        midpoint,
        right_mid,
        right,
        f_mid,
        f_right_mid,
        f_right,
        right_area,
        tolerance / 2.0,
        depth - 1,
    )


def _simpson(left: float, right: float, f_left: float, f_mid: float, f_right: float) -> float:
    return ((right - left) / 6.0) * (f_left + (4.0 * f_mid) + f_right)


def _compile_digit_masks_and_positions(board: Board) -> tuple[tuple[int, ...], tuple[Position, ...]]:
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

    return tuple(digit_masks), tuple(positions)


def _build_neighbor_masks(positions: tuple[Position, ...]) -> tuple[int, ...]:
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
    return tuple(neighbor_masks)


class _CompiledBoard:
    def __init__(self, board: Board) -> None:
        digit_masks, positions = _compile_digit_masks_and_positions(board)
        self._digit_masks = digit_masks
        self._positions = positions
        self._neighbor_masks = _build_neighbor_masks(positions)

    def trace_number(self, number: int) -> NumberTrace:
        if number < 0:
            raise ValueError(f"number must be non-negative; received {number}")

        digits = str(number)
        first_digit = int(digits[0])
        current_mask = self._digit_masks[first_digit]
        if current_mask == 0:
            return self._make_trace(
                number=number,
                digits=digits,
                readable=False,
                reason="digit_absent",
                failing_index=0,
                required_digit=first_digit,
                matched_prefix_length=0,
            )

        for digit_index, digit_char in enumerate(digits[1:], start=1):
            required_digit = int(digit_char)
            candidate_mask = self._digit_masks[required_digit]
            if candidate_mask == 0:
                return self._make_trace(
                    number=number,
                    digits=digits,
                    readable=False,
                    reason="digit_absent",
                    failing_index=digit_index,
                    required_digit=required_digit,
                    matched_prefix_length=digit_index,
                    frontier_mask=current_mask,
                )

            next_mask = self._advance(current_mask) & candidate_mask
            if next_mask == 0:
                return self._make_trace(
                    number=number,
                    digits=digits,
                    readable=False,
                    reason="digit_unreachable",
                    failing_index=digit_index,
                    required_digit=required_digit,
                    matched_prefix_length=digit_index,
                    frontier_mask=current_mask,
                    candidate_mask=candidate_mask,
                )

            current_mask = next_mask

        return self._make_trace(
            number=number,
            digits=digits,
            readable=True,
            reason="complete",
            failing_index=None,
            required_digit=None,
            matched_prefix_length=len(digits),
            frontier_mask=current_mask,
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

    def _make_trace(
        self,
        *,
        number: int,
        digits: str,
        readable: bool,
        reason: TraceReason,
        failing_index: int | None,
        required_digit: int | None,
        matched_prefix_length: int,
        frontier_mask: int = 0,
        candidate_mask: int = 0,
    ) -> NumberTrace:
        return NumberTrace(
            number=number,
            digits=digits,
            readable=readable,
            reason=reason,
            failing_index=failing_index,
            required_digit=required_digit,
            matched_prefix_length=matched_prefix_length,
            frontier=self._positions_from_mask(frontier_mask),
            candidate_positions=self._positions_from_mask(candidate_mask),
        )

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
    """Compatibility scorer matching the legacy board-search surface."""

    return evaluate_board(board).max_prefix


__all__ = [
    "BoardEvaluation",
    "NumberTrace",
    "Position",
    "TraceReason",
    "area_of_paper",
    "evaluate_board",
    "evaluate_prefix_visible_areas",
    "evaluate_visible_areas",
    "score_board",
    "trace_number",
]
