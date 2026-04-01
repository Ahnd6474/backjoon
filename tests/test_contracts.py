import inspect
from typing import get_type_hints

import solver
from solver import contracts


def test_solver_contract_exports_are_stable() -> None:
    triangle = solver.TrianglePaper(vertices=((0, 0), (2, 0), (0, 2)))
    circle = solver.CirclePaper(center=(1, -1), radius=3)

    assert solver.TRIANGLE_VERTEX_COUNT == 3
    assert triangle.kind == "triangle"
    assert triangle.vertices == ((0, 0), (2, 0), (0, 2))
    assert circle.kind == "circle"
    assert circle.center == (1, -1)
    assert circle.radius == 3
    assert solver.__all__ == [
        "CirclePaper",
        "Coordinate",
        "IncrementalVisibilitySolver",
        "IncrementalVisibleAreas",
        "Paper",
        "PaperStack",
        "Point",
        "Radius",
        "TRIANGLE_VERTEX_COUNT",
        "TrianglePaper",
        "TriangleVertices",
        "VisibleArea",
        "VisibleAreaEvaluator",
        "VisibleAreas",
    ]


def test_paper_parse_and_output_constants_define_the_submission_baseline() -> None:
    assert contracts.TRIANGLE_TYPE_CODE == 1
    assert contracts.CIRCLE_TYPE_CODE == 2
    assert contracts.VISIBLE_AREA_DECIMAL_PLACES == 12
    assert contracts.PREFIX_OUTPUT_ORDER == "rows follow input prefixes 1..N"
    assert contracts.ROW_VISIBLE_AREA_ORDER == "areas stay in paper input order within each prefix"

    assert contracts.SUBMISSION_TARGET.language == "c++17"
    assert contracts.SUBMISSION_TARGET.translation_units == 1
    assert contracts.SUBMISSION_TARGET.entrypoint == "main"
    assert contracts.SUBMISSION_TARGET.file_name == "main.cpp"


def test_callable_protocol_signatures_match_the_contract() -> None:
    parser_signature = inspect.signature(contracts.PaperInputParser.__call__)
    evaluator_signature = inspect.signature(contracts.VisibleAreaEvaluator.__call__)
    solver_signature = inspect.signature(contracts.IncrementalVisibilitySolver.__call__)
    formatter_signature = inspect.signature(contracts.VisibleAreaRowsFormatter.__call__)
    parser_hints = get_type_hints(contracts.PaperInputParser.__call__)
    evaluator_hints = get_type_hints(contracts.VisibleAreaEvaluator.__call__)
    solver_hints = get_type_hints(contracts.IncrementalVisibilitySolver.__call__)
    formatter_hints = get_type_hints(contracts.VisibleAreaRowsFormatter.__call__)

    assert list(parser_signature.parameters) == ["self", "text"]
    assert parser_hints["text"] == str
    assert parser_hints["return"] == contracts.PaperStack

    assert list(evaluator_signature.parameters) == ["self", "papers"]
    assert evaluator_hints["papers"] == contracts.PaperStack
    assert evaluator_hints["return"] == contracts.VisibleAreas

    assert list(solver_signature.parameters) == ["self", "evaluator", "papers"]
    assert solver_hints["evaluator"] == contracts.VisibleAreaEvaluator
    assert solver_hints["papers"] == contracts.PaperStack
    assert solver_hints["return"] == contracts.IncrementalVisibleAreas

    assert list(formatter_signature.parameters) == ["self", "rows"]
    assert formatter_hints["rows"] == contracts.VisibleAreaRows
    assert formatter_hints["return"] == str


def test_incremental_visible_area_shapes_are_explicit() -> None:
    papers: contracts.PaperStack = (
        contracts.CirclePaper(center=(0, 0), radius=1),
        contracts.TrianglePaper(vertices=((0, 0), (3, 0), (0, 3))),
    )
    prefix_outputs: contracts.IncrementalVisibleAreas = (
        (3.14159265359,),
        (2.356194490192, 2.0),
    )

    assert papers[0].kind == "circle"
    assert papers[1].kind == "triangle"
    assert prefix_outputs[0] == (3.14159265359,)
    assert prefix_outputs[1] == (2.356194490192, 2.0)

    row: contracts.VisibleAreaRow = prefix_outputs[1]
    rows: contracts.VisibleAreaRows = prefix_outputs
    assert row == (2.356194490192, 2.0)
    assert rows[-1] == row
