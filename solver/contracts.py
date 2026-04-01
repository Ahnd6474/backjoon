from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Protocol, TypeAlias

Coordinate: TypeAlias = int
Radius: TypeAlias = int
VisibleArea: TypeAlias = float
VisibleAreas: TypeAlias = tuple[VisibleArea, ...]
IncrementalVisibleAreas: TypeAlias = tuple[VisibleAreas, ...]

TRIANGLE_VERTEX_COUNT: Final[int] = 3

Point: TypeAlias = tuple[Coordinate, Coordinate]
TriangleVertices: TypeAlias = tuple[Point, Point, Point]


@dataclass(frozen=True, slots=True)
class TrianglePaper:
    """Triangle paper defined by its three vertices."""

    kind: Literal["triangle"] = "triangle"
    vertices: TriangleVertices = ((0, 0), (1, 0), (0, 1))


@dataclass(frozen=True, slots=True)
class CirclePaper:
    """Circle paper defined by its center point and radius."""

    kind: Literal["circle"] = "circle"
    center: Point = (0, 0)
    radius: Radius = 1


Paper: TypeAlias = TrianglePaper | CirclePaper
PaperStack: TypeAlias = tuple[Paper, ...]


class VisibleAreaEvaluator(Protocol):
    """Callable that returns the visible area for each paper in the current stack."""

    def __call__(self, papers: PaperStack, /) -> VisibleAreas:
        ...


class IncrementalVisibilitySolver(Protocol):
    """Callable that evaluates the stack after each paper is added in order."""

    def __call__(
        self,
        evaluator: VisibleAreaEvaluator,
        papers: PaperStack,
        /,
    ) -> IncrementalVisibleAreas:
        ...


# Compatibility aliases kept until the implementation modules migrate off the
# previous board-search vocabulary.
BOARD_ROWS: Final[int] = 8
BOARD_COLUMNS: Final[int] = 14
BOARD_SHAPE: Final[tuple[int, int]] = (BOARD_ROWS, BOARD_COLUMNS)
Digit: TypeAlias = int
BoardRow: TypeAlias = tuple[Digit, ...]
Board: TypeAlias = tuple[BoardRow, ...]
Score: TypeAlias = int
BoardEvaluator = VisibleAreaEvaluator
BoardSearch = IncrementalVisibilitySolver
