Generate a new pytest unit test suite for a FixFlux service component: $ARGUMENTS

Follow this repo's actual testing conventions — do not introduce `testcontainers`, `aiokafka`, or
a real broker/database anywhere in these tests. Every existing unit test suite in this repo mocks
the Kafka boundary via `unittest.mock.patch`; match that.

### Steps

1. Identify the target module (e.g. `services/<name>/src/<name>/consumer.py`) and read it in full
   before writing anything — don't assume its shape from the service name.
2. Identify what it depends on:
   - Kafka producer/consumer → constructed via `shared.infrastructure.kafka_client.create_producer`
     / `create_consumer`. Never patch these two functions directly if you can instead patch the
     underlying class one level down (`shared.infrastructure.kafka_client.KafkaProducer` /
     `KafkaConsumer`) — that's the pattern every existing `test_kafka_client.py` in this repo uses,
     and it's what lets a single patch target cover every service.
   - A Postgres session → patch `<service>.<module>.SessionLocal` where it's imported into the
     module under test, and build a `MagicMock` session (see any existing `test_*repository*.py`
     for the exact shape).
   - A FastAPI dependency (e.g. an injected producer) → use `app.dependency_overrides`, not a
     patch, if the route already uses `Depends()`.
3. Write tests as plain `pytest` functions or `TestXxx` classes with `test_xxx` methods — match
   whichever style the rest of that service's `tests/unit/` already uses (check one existing file
   in the same directory first).
4. Cover, at minimum:
   - The happy path.
   - Each distinct rejection/error branch — this repo's business logic (risk checks, compliance
     rules, order validation) is almost always a sequence of independent conditions; test each one
     in isolation with a fixture builder function (`_make_order(**overrides)` /
     `_checker(**overrides)` pattern — see `services/risk-service/tests/unit/test_checker.py`),
     not one giant end-to-end-in-miniature test.
   - Any regression the change under test is specifically meant to prevent — name the test after
     the regression, not just the code path (`test_toggling_enabled_after_construction_takes_effect`
     is preferred over `test_enabled_flag`).
5. Ensure the service's `pyproject.toml` has `pythonpath = ["src"]` under
   `[tool.pytest.ini_options]` — if it's missing, add it; don't just work around the missing config
   with `PYTHONPATH=` env var tricks in your own test run.
6. Run the new suite for real before declaring it done:
   ```bash
   cd services/<name> && python -m pytest -v
   ```
   Then check coverage against this repo's 85% gate:
   ```bash
   cd services/<name> && python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85
   ```
7. Run lint (`ruff check .`, `black --check .`, `isort --check-only .`, `mypy src/`) on the new
   test files too — test code is held to the same bar as production code in this repo's CI.

### What "done" looks like

- Every test passes with zero mocking of anything beyond the Kafka/DB/HTTP boundary — the actual
  business logic under test runs for real, unmocked.
- Coverage on the touched module is at or above 85%.
- No `testcontainers`, no `aiokafka`, no real network/DB connection anywhere in the suite.
