# Requires: GNU make + bash (Git Bash or WSL on Windows)
# Usage:
#   make test-unit         run all pytest unit tests
#   make test-integration  run behave integration tests (stack must already be running)
#   make test              unit + integration
#   make up                start docker-compose full stack
#   make down              stop stack and remove volumes
#   make clean             purge Python artifacts + dangling Docker images
#   make clean-all         down + clean

SHELL   := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.PHONY: test test-unit test-integration up down clean clean-python clean-docker clean-all

NS      := fixflux
COMPOSE := docker compose
BEHAVE  := python -m behave
PYTEST  := python -m pytest

# ── Python artifact cleanup ───────────────────────────────────────────────────
clean-python:
	@echo "Purging Python artifacts..."
	find . -type d -name '__pycache__'  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache'  -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -o -name '*.pyo' | xargs rm -f 2>/dev/null || true
	rm -rf logs/
	@echo "Done."

# ── Docker cleanup ────────────────────────────────────────────────────────────
clean-docker:
	@echo "Tearing down docker-compose stack and volumes..."
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	@echo "Pruning dangling images..."
	docker image prune -f
	@echo "Done."

clean: clean-python clean-docker

clean-all: down clean

# ── Stack lifecycle ───────────────────────────────────────────────────────────
up:
	$(COMPOSE) --profile full --profile monitoring up --build -d
	$(COMPOSE) ps

down:
	$(COMPOSE) down -v --remove-orphans

# ── Unit tests (pytest) ───────────────────────────────────────────────────────
test-unit:
	trap 'make clean-python' EXIT
	$(PYTEST) \
	    services/fix-gateway/tests/unit/ \
	    services/order-service/tests/unit/ \
	    services/matching-engine/tests/unit/ \
	    services/trade-store/tests/unit/ \
	    services/compliance-service/tests/unit/ \
	    -v --tb=short

# ── Integration tests (behave) ────────────────────────────────────────────────
# Assumes the stack (docker-compose or k8s) is already running.
# Cleans Python artifacts only - does not tear down the stack.
test-integration:
	trap 'make clean-python' EXIT
	cd tests/integration
	$(BEHAVE) $(BEHAVE_ARGS)

# ── Full test run ─────────────────────────────────────────────────────────────
test: test-unit test-integration
