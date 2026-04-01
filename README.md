# backjoon

`solve.cpp` is the single-file C++17 submission entrypoint for the visible-area paper stacking problem.

It reads the ACM input from standard input, evaluates each growing prefix in input order, and prints one output row per prefix. Each row contains the visible areas for papers `1..i`, formatted with 12 digits after the decimal point.

Example:

```text
$ g++ -O2 -std=c++17 solve.cpp -o solve
$ ./solve
2
2 0 0 1
1 0 0 2 0 0 2
3.141592653590
2.356194490192 2.000000000000
```

Useful local checks:

- `g++ -O2 -std=c++17 solve.cpp -o solve`
- `./solve`
- `python -m pytest`
