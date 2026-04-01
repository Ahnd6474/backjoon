from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Protocol, TypeAlias

Coordinate: TypeAlias = int
Radius: TypeAlias = int
VisibleArea: TypeAlias = float
VisibleAreas: TypeAlias = tuple[VisibleArea, ...]
VisibleAreaRow: TypeAlias = VisibleAreas
IncrementalVisibleAreas: TypeAlias = tuple[VisibleAreas, ...]
VisibleAreaRows: TypeAlias = IncrementalVisibleAreas
PaperTypeCode: TypeAlias = Literal[1, 2]

TRIANGLE_VERTEX_COUNT: Final[int] = 3
TRIANGLE_TYPE_CODE: Final[PaperTypeCode] = 1
CIRCLE_TYPE_CODE: Final[PaperTypeCode] = 2
VISIBLE_AREA_DECIMAL_PLACES: Final[int] = 12
PREFIX_OUTPUT_ORDER: Final[str] = "rows follow input prefixes 1..N"
ROW_VISIBLE_AREA_ORDER: Final[str] = "areas stay in paper input order within each prefix"

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


class PaperInputParser(Protocol):
    """Callable that parses the paper count followed by typed integer paper records."""

    def __call__(self, text: str, /) -> PaperStack:
        ...


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


class VisibleAreaRowsFormatter(Protocol):
    """Callable that emits one space-delimited visible-area row per evaluated prefix."""

    def __call__(self, rows: VisibleAreaRows, /) -> str:
        ...


@dataclass(frozen=True, slots=True)
class SubmissionTarget:
    """Final contest delivery target for the solver implementation."""

    language: Literal["c++17"] = "c++17"
    translation_units: Literal[1] = 1
    entrypoint: Literal["main"] = "main"
    file_name: str = "main.cpp"


SUBMISSION_TARGET: Final[SubmissionTarget] = SubmissionTarget()


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
