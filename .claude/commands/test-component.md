Run the full test suite for the service component at: $ARGUMENTS

Execute the following two commands in sequence from that directory, capturing output from both:

```bash
cd "$ARGUMENTS" && python -m pytest -v
```

```bash
cd "$ARGUMENTS" && python -m behave tests/bdd/features/
```

Print the full raw output of both commands verbatim, exactly as they would appear in a terminal session — including all test names, statuses, coverage tables, timing lines, warnings, and any error tracebacks. Do not truncate, summarise, or omit any lines.

After the raw output, append a concise summary:
- Unit tests: X passed, Y failed (or "no unit tests found")
- BDD tests:  X scenarios passed, Y failed (or "no BDD tests found")

If any tests failed, the failure details will already be visible in the full output above.
