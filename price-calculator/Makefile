.PHONY: help install test unit bdd coverage lint format clean

help:
	@echo "Available commands:"
	@echo "  make install   - Install dependencies"
	@echo "  make test      - Run all tests"
	@echo "  make unit      - Run unit tests only"
	@echo "  make bdd       - Run BDD tests only"
	@echo "  make coverage  - Run tests with coverage report"
	@echo "  make lint      - Run lint checks"
	@echo "  make format    - Auto-fix lint issues"
	@echo "  make clean     - Remove test artifacts"

install:
	pip install -r requirements.txt
	pip install -e .
	pre-commit install

test:
	pytest -v

unit:
	pytest tests/test_price.py -v

bdd:
	pytest tests/test_price_bdd.py --html=report.html --self-contained-html -v

coverage:
	pytest --cov=calculator --cov-report=term --cov-report=html --cov-fail-under=90

lint:
	pre-commit run --all-files

format:
	ruff check . --fix

clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage
	rm -f report.html
	rm -f logs.txt
