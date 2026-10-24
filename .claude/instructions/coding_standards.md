# FixFlux — Coding Standards

Grounded in what's actually enforced (CI, existing code), not aspirational rules. If you're
generating code for this repo, match the pattern of the service you're touching before reaching
for something more "modern" — consistency across ~10 services matters more than any one file being
individually clever.

## Sync is the default. Async is a deliberate, isolated exception.

Every consumer loop in this repo is synchronous `kafka-python` (not `aiokafka`), used the same way
everywhere:

```python
from shared.infrastructure.kafka_client import create_consumer

consumer = create_consumer("some_topic", "my-service-group")
for msg in consumer:
    handle(msg.value)
```

FastAPI routes in `trade-store` and `compliance-service` are plain `def`, not `async def` — they
don't do anything that benefits from async (SQLAlchemy sessions are synchronous throughout this
codebase; there is no async ORM usage anywhere).

**The one exception is `market-data-api`**, and it's an exception for a specific reason: it holds
open WebSocket connections and must broadcast to them without blocking. Its Kafka consumer still
runs synchronously on a background thread (same `create_consumer` factory as everywhere else) —
async was only introduced at the WebSocket/broadcast layer, bridged from the sync thread via
`asyncio.run_coroutine_threadsafe(coro, loop)`. Do not reach for `aiokafka` — if a new service
needs both a consumer loop and async I/O, follow that same pattern (sync consumer thread +
`run_coroutine_threadsafe` bridge) rather than introducing a second Kafka client library.

## Pydantic v2

Every schema is Pydantic v2. Use v2 idioms explicitly:
- `model.model_dump(mode="json")` — not `.dict()`.
- `model_config` / field validators — not the v1 `class Config:` inner class, if you need either.

Reserve Pydantic models for things crossing a Kafka or HTTP boundary. In-process, mutated-in-a-hot-
loop objects (see `matching_engine.models.Order`) are plain `@dataclass` — don't "upgrade" them to
Pydantic; the cost of validation on every mutation isn't worth it for something that never gets
serialized directly.

## Type hints

Type-hint function signatures (params + return type). Prefer built-in generics (`list[str]`,
`dict[str, Any]`, `X | None`) over `typing.List`/`Optional` — this repo targets Python 3.11+.
`mypy` runs in CI with `ignore_missing_imports = true` and `explicit_package_bases = true`; match
that config in any new service's `pyproject.toml` rather than inventing a stricter one, unless
asked.

## Logging

```python
from shared.observability.log_config import configure_logging, get_logger

configure_logging()  # call once, at module import time, before anything logs
logger = get_logger(__name__)
```

- `LOG_LEVEL` env var (default `INFO`), `LOG_FORMAT` env var (`plain` default, `json` for
  structured output via the built-in `JsonFormatter`).
- Log the *decision*, not just the event: risk-service and matching-engine both log a single line
  per decision with every relevant field inline (`f"pre_trade_decision | order={...} decision=..."`)
  rather than several scattered log statements — this is what the Grafana Loki dashboards' LogQL
  queries are written against, so don't change that shape without checking
  `infrastructure/monitoring/grafana/dashboards/loki_logs.json` first.

## Testing

- **Never construct a raw `KafkaProducer`/`KafkaConsumer` in a test.** Patch the shared factory's
  underlying class directly — this one patch target covers every service in the repo:
  ```python
  @patch("shared.infrastructure.kafka_client.KafkaProducer")
  def test_x(self, mock_cls):
      mock_cls.return_value = MagicMock()
      ...
  ```
- No `testcontainers`. This repo doesn't use it anywhere. Unit tests mock the Kafka boundary as
  above; cross-service behavior is tested with `behave` (BDD) against the real, running
  docker-compose stack (`tests/integration/`, or a service's own `tests/bdd/`) — not ephemeral
  per-test containers.
- Every service's `pyproject.toml` needs `[tool.pytest.ini_options]` with `pythonpath = ["src"]`
  and `testpaths = ["tests/unit"]` so `pytest` works without a prior `pip install`. Add this from
  the start on a new service — it's easy to forget and only surfaces as a confusing
  `ModuleNotFoundError` later.
- CI enforces `--cov-fail-under=85` per service (compliance-service, fix-gateway,
  market-data-service, matching-engine, order-service, risk-service, trade-store). Match that bar
  in any new service's workflow rather than inventing a different number.
- FastAPI routes with an injected dependency (e.g. a Kafka producer) should use `Depends()` +
  `functools.lru_cache` so tests can swap it via `app.dependency_overrides`, never a real broker:
  ```python
  @lru_cache
  def get_producer() -> InjectorProducer:
      return InjectorProducer()

  # in a test:
  app.dependency_overrides[get_producer] = lambda: fake_producer
  ```
  Ruff's B008 rule flags `Depends(...)` as a mutable-default-in-signature false positive here —
  the fix is `extend-immutable-calls = ["fastapi.Depends"]` under
  `[tool.ruff.lint.flake8-bugbear]` in `pyproject.toml`, not restructuring the DI pattern away.

## Lint / format

`ruff` + `black` + `isort` + `mypy`, line-length 88, target `py311`, `isort` profile `black`. Copy
an existing service's `pyproject.toml` `[tool.*]` sections verbatim when starting a new one rather
than reconfiguring from scratch.

**First-party imports must be declared twice**, once per tool, because ruff does not read
`[tool.isort]`:

```toml
[tool.ruff.lint.isort]
known-first-party = ["<service_package>", "shared"]

[tool.isort]
profile = "black"
known_first_party = ["<service_package>", "shared"]
```

With only `[tool.isort]`, isort groups `shared` with the service package while ruff treats it as
third-party, and ruff's `I001` fails on imports isort considers correctly sorted. Neither tool's
auto-fix can satisfy both. That's how `clients/fix-replay` broke CI (2026-10): its config was
copied from `market-data-service`, which was missing the ruff section at the time.

**ruff is pinned to `0.17.2`** in every workflow's `pip install` line and in the root
`requirements-dev.txt`. Lint locally with the same version, because newer releases enable more
rules by default (observed: 0.17.2 enforces `I` import sorting and `RUF100` unused-`noqa` with this
repo's config; 0.15.1 enforced neither). A local run on a different ruff can pass while CI fails on
identical code. Before calling lint clean:

```bash
python -m pip install ruff==0.17.2 && python -m ruff --version
python -m ruff check . && python -m black --check . && python -m isort --check-only . && python -m mypy src/
```

To upgrade ruff, change the pin everywhere in one commit (`grep -rn "ruff==" .github
requirements-dev.txt`) and run the new version across every service first. New workflows must pin
it too. `black`, `isort` and `mypy` are still unpinned and can drift the same way.

**Only add `# noqa: <code>` for a rule that is actually enabled.** Check with
`ruff check --show-settings <file> | grep <code>`. A `noqa` for a disabled rule (e.g. `S310`;
the `S` bandit rules are not enabled here) is itself an error under `RUF100`.

**A lint fix isn't done until it's pushed.** CI lints the pushed commit, not the working tree.
When a CI failure "reappears" after a local fix, check `git status` and
`git show origin/<branch>:<path>` before changing code again.
