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


def test_callable_protocol_signatures_match_the_contract() -> None:
    evaluator_signature = inspect.signature(contracts.VisibleAreaEvaluator.__call__)
    solver_signature = inspect.signature(contracts.IncrementalVisibilitySolver.__call__)
    evaluator_hints = get_type_hints(contracts.VisibleAreaEvaluator.__call__)
    solver_hints = get_type_hints(contracts.IncrementalVisibilitySolver.__call__)

    assert list(evaluator_signature.parameters) == ["self", "papers"]
    assert evaluator_hints["papers"] == contracts.PaperStack
    assert evaluator_hints["return"] == contracts.VisibleAreas

    assert list(solver_signature.parameters) == ["self", "evaluator", "papers"]
    assert solver_hints["evaluator"] == contracts.VisibleAreaEvaluator
    assert solver_hints["papers"] == contracts.PaperStack
    assert solver_hints["return"] == contracts.IncrementalVisibleAreas


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
