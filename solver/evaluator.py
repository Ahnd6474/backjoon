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


@dataclass(frozen=True)
class _LineFunction:
    slope: float
    intercept: float

    def value_at(self, x: float) -> float:
        return (self.slope * x) + self.intercept

    def integral(self, left: float, right: float) -> float:
        return (0.5 * self.slope * ((right * right) - (left * left))) + (
            self.intercept * (right - left)
        )


@dataclass(frozen=True)
class _CircleFunction:
    center_x: float
    center_y: float
    radius: float
    sign: int

    def value_at(self, x: float) -> float:
        delta = max(0.0, (self.radius * self.radius) - ((x - self.center_x) ** 2))
        return self.center_y + (self.sign * math.sqrt(delta))

    def integral(self, left: float, right: float) -> float:
        return _circle_integral(self, right) - _circle_integral(self, left)


BoundaryFunction: TypeAlias = _LineFunction | _CircleFunction


@dataclass(frozen=True)
class _ShapeSlab:
    left: float
    right: float
    lower: BoundaryFunction
    upper: BoundaryFunction


@dataclass(frozen=True)
class _ShapeProfile:
    xmin: float
    xmax: float
    slabs: tuple[_ShapeSlab, ...]


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
    target_profile = _build_shape_profile(target)
    if target_profile.xmax - target_profile.xmin <= _EPS:
        return 0.0

    relevant_profiles = tuple(
        profile
        for profile in (_build_shape_profile(occluder) for occluder in occluders)
        if profile.xmin <= target_profile.xmax + _EPS and profile.xmax >= target_profile.xmin - _EPS
    )
    breakpoints = _collect_breakpoints(target_profile, relevant_profiles)
    target_area = _integrate_target_profile(target_profile)
    covered_area = 0.0
    for left, right in zip(breakpoints, breakpoints[1:]):
        if right - left <= _EPS:
            continue
        covered_area += _covered_area_in_slab(target_profile, relevant_profiles, left, right)
    visible_area = target_area - covered_area
    if abs(visible_area) <= _AREA_TOLERANCE:
        return 0.0
    return max(0.0, visible_area)


def _build_shape_profile(paper: Paper) -> _ShapeProfile:
    if isinstance(paper, CirclePaper):
        center_x, center_y = paper.center
        radius = float(paper.radius)
        slab = _ShapeSlab(
            left=center_x - radius,
            right=center_x + radius,
            lower=_CircleFunction(center_x=float(center_x), center_y=float(center_y), radius=radius, sign=-1),
            upper=_CircleFunction(center_x=float(center_x), center_y=float(center_y), radius=radius, sign=1),
        )
        return _ShapeProfile(xmin=slab.left, xmax=slab.right, slabs=(slab,))

    xs = sorted({float(vertex[0]) for vertex in paper.vertices})
    slabs: list[_ShapeSlab] = []
    for left, right in zip(xs, xs[1:]):
        if right - left <= _EPS:
            continue
        midpoint = (left + right) / 2.0
        active_lines = [
            line
            for start, end in _triangle_edges(paper)
            if (line := _line_function_for_edge(start, end)) is not None
            and _x_within_edge(midpoint, start, end)
        ]
        if len(active_lines) < 2:
            continue
        active_lines.sort(key=lambda function: function.value_at(midpoint))
        slabs.append(_ShapeSlab(left=left, right=right, lower=active_lines[0], upper=active_lines[-1]))

    if not slabs:
        xmin = float(min(vertex[0] for vertex in paper.vertices))
        return _ShapeProfile(xmin=xmin, xmax=xmin, slabs=())

    return _ShapeProfile(xmin=slabs[0].left, xmax=slabs[-1].right, slabs=tuple(slabs))


def _collect_breakpoints(target: _ShapeProfile, occluders: tuple[_ShapeProfile, ...]) -> tuple[float, ...]:
    points = {target.xmin, target.xmax}
    slabs = _collect_relevant_slabs(target, occluders, points)

    for point in _collect_boundary_intersections(target, slabs):
        points.add(point)

    return tuple(sorted(points))


def _integrate_target_profile(profile: _ShapeProfile) -> float:
    return sum(
        slab.upper.integral(slab.left, slab.right) - slab.lower.integral(slab.left, slab.right)
        for slab in profile.slabs
    )


def _covered_area_in_slab(
    target: _ShapeProfile,
    occluders: tuple[_ShapeProfile, ...],
    left: float,
    right: float,
) -> float:
    midpoint = (left + right) / 2.0
    target_slab = _find_slab(target.slabs, midpoint)
    if target_slab is None:
        return 0.0

    clipped_intervals = _collect_clipped_intervals(target_slab, occluders, midpoint)

    if not clipped_intervals:
        return 0.0

    return _merge_clipped_interval_area(clipped_intervals, left, right, midpoint)


def _collect_relevant_slabs(
    target: _ShapeProfile,
    occluders: tuple[_ShapeProfile, ...],
    points: set[float],
) -> list[_ShapeSlab]:
    slabs = [*target.slabs]
    for occluder in occluders:
        for slab in occluder.slabs:
            clipped = _clip_slab_to_target(target, slab)
            if clipped is None:
                continue
            points.add(clipped.left)
            points.add(clipped.right)
            slabs.append(clipped)
    return slabs


def _clip_slab_to_target(target: _ShapeProfile, slab: _ShapeSlab) -> _ShapeSlab | None:
    left = max(target.xmin, slab.left)
    right = min(target.xmax, slab.right)
    if right - left <= _EPS:
        return None
    return _ShapeSlab(left=left, right=right, lower=slab.lower, upper=slab.upper)


def _collect_boundary_intersections(
    target: _ShapeProfile,
    slabs: list[_ShapeSlab],
) -> tuple[float, ...]:
    points: set[float] = set()
    boundary_pieces = _boundary_pieces(slabs)
    for index, (left1, right1, function1) in enumerate(boundary_pieces):
        for left2, right2, function2 in boundary_pieces[index + 1 :]:
            left = max(target.xmin, left1, left2)
            right = min(target.xmax, right1, right2)
            if right - left <= _EPS:
                continue
            for point in _function_intersections(function1, function2, left, right):
                if left + _EPS < point < right - _EPS:
                    points.add(point)
    return tuple(sorted(points))


def _boundary_pieces(slabs: list[_ShapeSlab]) -> list[tuple[float, float, BoundaryFunction]]:
    pieces: list[tuple[float, float, BoundaryFunction]] = []
    for slab in slabs:
        pieces.append((slab.left, slab.right, slab.lower))
        pieces.append((slab.left, slab.right, slab.upper))
    return pieces


def _collect_clipped_intervals(
    target_slab: _ShapeSlab,
    occluders: tuple[_ShapeProfile, ...],
    midpoint: float,
) -> list[tuple[BoundaryFunction, BoundaryFunction]]:
    clipped_intervals: list[tuple[BoundaryFunction, BoundaryFunction]] = []
    for occluder in occluders:
        occluder_slab = _find_slab(occluder.slabs, midpoint)
        if occluder_slab is None:
            continue
        clipped = _clip_occluder_interval(target_slab, occluder_slab, midpoint)
        if clipped is not None:
            clipped_intervals.append(clipped)
    return clipped_intervals


def _clip_occluder_interval(
    target_slab: _ShapeSlab,
    occluder_slab: _ShapeSlab,
    midpoint: float,
) -> tuple[BoundaryFunction, BoundaryFunction] | None:
    target_lower = target_slab.lower.value_at(midpoint)
    target_upper = target_slab.upper.value_at(midpoint)
    occluder_lower = occluder_slab.lower.value_at(midpoint)
    occluder_upper = occluder_slab.upper.value_at(midpoint)

    lower = occluder_slab.lower if occluder_lower >= target_lower - _EPS else target_slab.lower
    upper = occluder_slab.upper if occluder_upper <= target_upper + _EPS else target_slab.upper
    if upper.value_at(midpoint) - lower.value_at(midpoint) <= _EPS:
        return None
    return lower, upper


def _merge_clipped_interval_area(
    clipped_intervals: list[tuple[BoundaryFunction, BoundaryFunction]],
    left: float,
    right: float,
    midpoint: float,
) -> float:
    clipped_intervals.sort(key=lambda interval: interval[0].value_at(midpoint))
    merged_area = 0.0
    current_lower, current_upper = clipped_intervals[0]
    for next_lower, next_upper in clipped_intervals[1:]:
        if next_lower.value_at(midpoint) > current_upper.value_at(midpoint) + _EPS:
            merged_area += current_upper.integral(left, right) - current_lower.integral(left, right)
            current_lower, current_upper = next_lower, next_upper
            continue
        if next_upper.value_at(midpoint) > current_upper.value_at(midpoint) + _EPS:
            current_upper = next_upper

    merged_area += current_upper.integral(left, right) - current_lower.integral(left, right)
    return merged_area


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


def _triangle_edges(paper: TrianglePaper) -> tuple[tuple[Position, Position], ...]:
    vertices = paper.vertices
    return tuple(zip(vertices, (*vertices[1:], vertices[0])))


def _line_function_for_edge(start: Position, end: Position) -> _LineFunction | None:
    x1, y1 = start
    x2, y2 = end
    if abs(x1 - x2) <= _EPS:
        return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - (slope * x1)
    return _LineFunction(slope=float(slope), intercept=float(intercept))


def _x_within_edge(x: float, start: Position, end: Position) -> bool:
    lower_x = min(start[0], end[0])
    upper_x = max(start[0], end[0])
    return lower_x - _EPS <= x <= upper_x + _EPS


def _find_slab(slabs: tuple[_ShapeSlab, ...], x: float) -> _ShapeSlab | None:
    for slab in slabs:
        if slab.left - _EPS <= x <= slab.right + _EPS:
            return slab
    return None


def _function_intersections(
    left: BoundaryFunction,
    right: BoundaryFunction,
    xmin: float,
    xmax: float,
) -> tuple[float, ...]:
    if isinstance(left, _LineFunction) and isinstance(right, _LineFunction):
        return _line_line_intersections(left, right, xmin, xmax)
    if isinstance(left, _LineFunction) and isinstance(right, _CircleFunction):
        return _line_circle_intersections(left, right, xmin, xmax)
    if isinstance(left, _CircleFunction) and isinstance(right, _LineFunction):
        return _line_circle_intersections(right, left, xmin, xmax)
    return _circle_circle_intersections(left, right, xmin, xmax)


def _line_line_intersections(
    left: _LineFunction,
    right: _LineFunction,
    xmin: float,
    xmax: float,
) -> tuple[float, ...]:
    slope_delta = left.slope - right.slope
    if abs(slope_delta) <= _EPS:
        return ()
    point = (right.intercept - left.intercept) / slope_delta
    if xmin - _EPS <= point <= xmax + _EPS:
        return (point,)
    return ()


def _line_circle_intersections(
    line: _LineFunction,
    circle: _CircleFunction,
    xmin: float,
    xmax: float,
) -> tuple[float, ...]:
    shifted_intercept = line.intercept - circle.center_y
    qa = 1.0 + (line.slope * line.slope)
    qb = (2.0 * line.slope * shifted_intercept) - (2.0 * circle.center_x)
    qc = (circle.center_x * circle.center_x) + (shifted_intercept * shifted_intercept) - (
        circle.radius * circle.radius
    )
    discriminant = (qb * qb) - (4.0 * qa * qc)
    if discriminant < -_EPS:
        return ()
    discriminant = max(0.0, discriminant)
    sqrt_discriminant = math.sqrt(discriminant)
    roots = {
        (-qb - sqrt_discriminant) / (2.0 * qa),
        (-qb + sqrt_discriminant) / (2.0 * qa),
    }
    matches: list[float] = []
    for root in roots:
        if not (xmin - _EPS <= root <= xmax + _EPS):
            continue
        if abs(line.value_at(root) - circle.value_at(root)) <= 1e-9:
            matches.append(root)
    return tuple(sorted(matches))


def _circle_circle_intersections(
    left: _CircleFunction,
    right: _CircleFunction,
    xmin: float,
    xmax: float,
) -> tuple[float, ...]:
    dx = right.center_x - left.center_x
    dy = right.center_y - left.center_y
    distance = math.hypot(dx, dy)
    if distance <= _EPS:
        return ()
    if distance > left.radius + right.radius + _EPS:
        return ()
    if distance < abs(left.radius - right.radius) - _EPS:
        return ()

    a = ((left.radius * left.radius) - (right.radius * right.radius) + (distance * distance)) / (2.0 * distance)
    h_sq = (left.radius * left.radius) - (a * a)
    if h_sq < -_EPS:
        return ()
    h = math.sqrt(max(0.0, h_sq))
    x_mid = left.center_x + (a * dx / distance)
    y_mid = left.center_y + (a * dy / distance)
    offset_x = -dy * h / distance
    offset_y = dx * h / distance
    candidates = {(x_mid + offset_x, y_mid + offset_y), (x_mid - offset_x, y_mid - offset_y)}

    matches: list[float] = []
    for x, y in candidates:
        if not (xmin - _EPS <= x <= xmax + _EPS):
            continue
        if abs(y - left.value_at(x)) <= 1e-9 and abs(y - right.value_at(x)) <= 1e-9:
            matches.append(x)
    return tuple(sorted(set(matches)))


def _circle_integral(function: _CircleFunction, x: float) -> float:
    clamped = min(function.center_x + function.radius, max(function.center_x - function.radius, x))
    shifted = clamped - function.center_x
    radius = function.radius
    ratio = 0.0 if radius <= _EPS else max(-1.0, min(1.0, shifted / radius))
    root = math.sqrt(max(0.0, (radius * radius) - (shifted * shifted)))
    circular = 0.5 * ((shifted * root) + ((radius * radius) * math.asin(ratio)))
    return (function.center_y * clamped) + (function.sign * circular)


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
