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

### One-time setup

From the repo root (works the same in PowerShell and bash):

```bash
pip install -r fixflux/tests/ui/requirements.txt   # Playwright pinned (route_web_socket needs >= 1.48)
python -m playwright install chromium              # one-off browser download
```

compliance-service and `shared` must be importable. If they aren't installed yet, run
`pip install -e ./shared -e ./services/compliance-service` from `fixflux/`. `environment.py` also
adds the source folders to `sys.path`.

### Run the tests

Always run from `fixflux/tests/ui`, where `behave.ini` lives.

**PowerShell (Windows):**

```powershell
cd C:\Dev\python-engineering-lab\fixflux\tests\ui

python -m behave                                        # all scenarios, headless (~2s)
python -m behave features/market_data.feature           # one feature
python -m behave -n "Valid FIX orders"                  # scenarios whose name matches

# Watch the browser, slowed down (e.g. for demo footage)
$env:UI_HEADED = "1"; $env:UI_SLOW_MO = "300"; python -m behave
Remove-Item Env:UI_HEADED, Env:UI_SLOW_MO               # back to headless
```

**bash / Git Bash / Linux / macOS:**

```bash
cd fixflux/tests/ui
python -m behave                                        # all scenarios, headless (~2s)
python -m behave features/market_data.feature           # one feature
UI_HEADED=1 UI_SLOW_MO=300 python -m behave             # watch it run, slowed down
```

`python -m behave` uses the same Python that `pip` installed into. A bare `behave` can pick up a
different installation's script if several Pythons are on your PATH.

A failed scenario saves a Playwright trace to `artifacts/` (gitignored). Open it with
`playwright show-trace artifacts/<name>.zip`. In CI (`.github/workflows/ui-tests.yml`) traces are
uploaded as a build artifact.

## Run on GitHub Actions

The workflow is **Console UI Tests** (`.github/workflows/ui-tests.yml`). One run lints the test
code, then runs every scenario headless on Ubuntu.

### Automatically

It runs on any push or pull request that changes one of these paths:

- `fixflux/tests/ui/**`
- `fixflux/services/compliance-service/src/compliance_service/templates/**`
- `fixflux/services/compliance-service/src/compliance_service/api/**`
- `fixflux/services/compliance-service/src/compliance_service/static/**`
- `.github/workflows/ui-tests.yml`

Changes anywhere else, e.g. to market-data-api, don't trigger it. Use a manual run for those.

### Manually, from the website

1. Open the repo's **Actions** tab:
   <https://github.com/NEMETOM/python-engineering-lab/actions/workflows/ui-tests.yml>
2. Click **Run workflow** (top right of the runs list).
3. Pick the branch to test, e.g. `fix-flux`, and click the green **Run workflow** button.

The button only appears because the workflow file is on the default branch (`main`). The
branch you pick runs its own copy of the tests.

### Manually, from the terminal (GitHub CLI)

Needs the [GitHub CLI](https://cli.github.com/) installed and logged in (`gh auth login`). For
Windows install steps, see [GITHUB_CLI_SETUP.md](GITHUB_CLI_SETUP.md).

```bash
gh workflow run ui-tests.yml --ref fix-flux        # start a run on a branch
gh run list --workflow=ui-tests.yml --limit 5      # find it
gh run watch                                       # follow the latest run live
```

### Test report

Every run (passed or failed) publishes a **Console UI Tests (Playwright + behave)** check, built
from behave's JUnit output by `dorny/test-reporter`. It lists each feature and scenario with its
result, and for failures shows the assertion message, e.g. `expected '174.90', actual 174.90000`.
Find it under the run's **Checks** tab, or next to the commit/PR status.

Locally, `python -m behave --junit --junit-directory reports/` writes the same XML (gitignored).

### When a scenario fails in CI

The run uploads a **playwright-traces** artifact with one trace per failed scenario. Download it
from the bottom of the run's summary page, or with `gh run download <run-id> --name playwright-traces`,
then open a trace locally with `python -m playwright show-trace <name>.zip`. It shows a
step-by-step replay with screenshots, DOM snapshots and network calls.

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
