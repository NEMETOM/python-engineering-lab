# FixFlux Console UI tests

Playwright + behave tests for the three Console tabs: **Fix Msg Injector**, **Compliance Rules**
and **Market Data**. Happy paths only for now. Every scenario is a `Scenario Outline` with at
least 2 `Examples` rows.

## How it works

These tests are **hermetic**: no Docker stack, no Kafka, no Postgres. `environment.py` runs the
real compliance-api FastAPI app in a background thread and fakes only its outside world:

| Real dependency | Replaced by |
|---|---|
| Kafka producer (injector → `raw_orders`) | `FakeProducer`, which records events (FastAPI dependency override) |
| Postgres `compliance_rule_overrides` | `FakeOverrideRepository`, in memory, reset per scenario |
| market-data-api WebSocket (`:8006/ws/market-data`) | `page.route_web_socket`: steps push snapshots into the browser |
| Tailwind CDN | A one-line stub defining `.hidden`, so tests run offline and show/hide still works |

Everything else is real: routes, templates, the rule catalogue and policies, and the page
JavaScript. Each scenario gets a fresh browser context.

## Run

```bash
pip install -r fixflux/tests/ui/requirements.txt   # Playwright pinned (route_web_socket needs >= 1.48)
python -m playwright install chromium              # one-off browser download
cd fixflux/tests/ui
behave                                             # headless, ~2s for all scenarios
UI_HEADED=1 UI_SLOW_MO=300 behave                  # watch it run, e.g. for demo footage
```

compliance-service and `shared` must be importable, e.g. `pip install -e ./shared -e ./services/compliance-service`
from `fixflux/`. `environment.py` also adds the source folders to `sys.path`.

A failed scenario saves a Playwright trace to `artifacts/` (gitignored). Open it with
`playwright show-trace artifacts/<name>.zip`. In CI (`.github/workflows/ui-tests.yml`) traces are
uploaded as a build artifact.

## Layout

```
tests/ui/
├── behave.ini          paths = features, steps_dir = steps
├── pyproject.toml      lint config (declares pages/ first-party for ruff AND isort)
├── environment.py      server, fakes, browser lifecycle, traces on failure
├── features/           one .feature per tab, plus navigation
├── pages/              page objects: every locator lives here
│   ├── console.py              ConsolePage base + ConsoleNav (shared tab bar)
│   ├── injector_page.py        InjectorPage
│   ├── compliance_rules_page.py ComplianceRulesPage, RuleCard
│   └── market_data_page.py     MarketDataPage, QuoteRow
└── steps/              one steps module per feature; intent + assertions only
```

## Conventions

- **Page objects own every locator.** Steps never call `page.locator()` or `get_by_*` directly.
  They go through `InjectorPage`, `ComplianceRulesPage`, `MarketDataPage` or `ConsolePage.nav`.
  When a template changes, only the matching page object changes.
- **Page objects don't assert.** They return Playwright `Locator`s and perform actions
  (`inject(lines)`, `rule(id).toggle()`, `nav.open_tab(name)`). Assertions stay in the steps,
  with `expect(...)`, so a scenario's verdicts are readable in one place.
- **Locators:** roles first (`get_by_role("link", name=...)`, `get_by_role("switch")`), then the
  `data-testid` hooks in the templates (`rule-card`, `rule-badge`, `quote-row`, `cell-*`). The
  active tab carries `aria-current="page"`.
- **Waiting:** only Playwright's auto-waiting `expect(...)`, never `sleep`.
- **Fakes from steps:** use what `before_all` puts on `context` (e.g. `context.override_repo`),
  never `import environment`. behave executes `environment.py` itself, so importing it loads a
  second copy with separate state.
