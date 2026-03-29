Run all lint checks: ruff, black, isort, and mypy on the current project directory.

```bash
echo "=== Ruff ===" && python -m ruff check .
echo "=== Black ===" && python -m black --check .
echo "=== Isort ===" && python -m isort --check-only .
echo "=== MyPy ===" && python -m mypy . --pretty --show-error-codes
```
