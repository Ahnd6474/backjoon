# backjoon

`solve.py` is the submission entrypoint for the visible-area paper stacking problem.

It reads the problem input from standard input, evaluates each growing prefix with the repository's geometry evaluator and incremental search pipeline, and prints one output row per prefix. Each row contains the visible areas for papers `1..i`, formatted with 12 digits after the decimal point.

Example:

```text
$ python solve.py
2
2 0 0 1
1 0 0 2 0 0 2
3.141592653590
2.356194490120 2.000000000000
```

Useful local checks:

- `python solve.py`
- `python -m pytest`
