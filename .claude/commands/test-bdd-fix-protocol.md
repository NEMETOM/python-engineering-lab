Run all BDD tests for the fixflux project.

This covers three layers in sequence:
1. Component BDD tests for each of the 5 services
2. Shared module BDD tests
3. Integration BDD tests (persistence only — PostgreSQL must be running; Kafka tests are skipped)

Execute each block below in sequence from the repo root. Print the full raw output of every command verbatim — all scenario names, step results, timing lines, warnings, and any error tracebacks. Do not truncate, summarise, or omit any lines.

---

**Component BDD — fix-gateway**
```bash
cd fixflux/services/fix-gateway && python -m behave tests/bdd/features/
```

**Component BDD — order-service**
```bash
cd fixflux/services/order-service && python -m behave tests/bdd/features/
```

**Component BDD — matching-engine**
```bash
cd fixflux/services/matching-engine && python -m behave tests/bdd/features/
```

**Component BDD — market-data-service**
```bash
cd fixflux/services/market-data-service && python -m behave tests/bdd/features/
```

**Component BDD — trade-store**
```bash
cd fixflux/services/trade-store && python -m behave tests/bdd/features/
```

**Shared BDD**
```bash
cd fixflux/shared && python -m behave
```

**Integration BDD (persistence, no Kafka)**
```bash
cd fixflux/tests/integration && python -m behave features/ --tags="@integration" --tags="~@needs_kafka"
```

---

After all output, append a summary table:

| Suite | Scenarios passed | Scenarios failed |
|---|---|---|
| fix-gateway BDD | ? | ? |
| order-service BDD | ? | ? |
| matching-engine BDD | ? | ? |
| market-data-service BDD | ? | ? |
| trade-store BDD | ? | ? |
| shared BDD | ? | ? |
| integration (persistence) | ? | ? |

If any suite produced failures, note which ones clearly at the end.
