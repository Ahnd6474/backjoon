from solver.evaluator import evaluate_board, trace_number


def make_board(*rows: str) -> tuple[tuple[int, ...], ...]:
    assert len(rows) == 8
    assert all(len(row) == 14 for row in rows)
    return tuple(tuple(int(char) for char in row) for row in rows)


def test_evaluate_board_reports_first_absent_digit() -> None:
    board = make_board(
        "12000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
    )

    result = evaluate_board(board)

    assert result.max_prefix == 2
    assert result.first_missing == 3
    assert result.witness.reason == "digit_absent"
    assert result.witness.failing_index == 0
    assert result.witness.required_digit == 3
    assert result.witness.frontier == ()
    assert result.witness.candidate_positions == ()


def test_trace_number_allows_revisits_but_not_waiting_in_place() -> None:
    board = make_board(
        "12000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
        "00000000000000",
    )

    revisiting_trace = trace_number(board, 121)
    waiting_trace = trace_number(board, 11)

    assert revisiting_trace.readable is True
    assert revisiting_trace.reason == "complete"
    assert revisiting_trace.frontier == ((0, 0),)

    assert waiting_trace.readable is False
    assert waiting_trace.reason == "digit_unreachable"
    assert waiting_trace.failing_index == 1
    assert waiting_trace.frontier == ((0, 0),)
    assert waiting_trace.candidate_positions == ((0, 0),)


def test_evaluate_board_reports_unreachable_next_digit_with_witness() -> None:
    board = make_board(
        "12345678999999",
        "99999999999999",
        "99999999999999",
        "99999999999999",
        "99999999999999",
        "99999999999999",
        "99999999999999",
        "00000000000000",
    )

    result = evaluate_board(board)

    assert result.max_prefix == 9
    assert result.first_missing == 10
    assert result.witness.reason == "digit_unreachable"
    assert result.witness.failing_index == 1
    assert result.witness.required_digit == 0
    assert result.witness.frontier == ((0, 0),)
    assert result.witness.candidate_positions[0] == (7, 0)
    assert result.witness.candidate_positions[-1] == (7, 13)
