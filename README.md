# backjoon

`python solve.py` prints the committed 8x14 digit grid and nothing else.

The checked-in board was selected from the current deterministic search pipeline by running `search_board_with_result(score_board)` against the shared evaluator. The locked candidate in this branch has score `1906` and source `serpentine:r1c0`.

Useful local checks:

- `python solve.py`
- `python -c "import solve; print(solve.inspect_final_result())"`
- `python -m pytest`
