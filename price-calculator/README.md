> A production-style Python mini-project showcasing clean architecture, BDD, structured logging, and enterprise-grade CI/CD with GitHub Actions.  
> Built to demonstrate not just coding ability, but professional software engineering practices including coverage enforcement, traceable logging, and PR-based quality gates.


# Price Calculator (Python)

A fully tested and enterprise-ready Python mini-project demonstrating clean architecture, modern testing practices, and professional-grade CI/CD pipelines.

---

## 🚀 Features

- **Accurate Price Calculations**
  - Apply discounts and add VAT with proper validation.
  - Handles edge cases like negative prices or invalid discounts.

- **Testing**
  - ✅ Unit tests with `pytest`
  - ✅ BDD tests with `pytest-bdd` and Gherkin feature files
  - ✅ Negative test cases for invalid inputs
  - ✅ Floating-point safe assertions using `pytest.approx`

- **CI/CD**
  - GitHub Actions pipeline with:
    - Multi-Python version matrix
    - Code coverage enforcement (90%+)
    - PR-only BDD job
    - HTML reports and log artifacts

- **Logging & Observability**
  - JSON structured logging with correlation IDs
  - Environment-based log levels
  - Log output saved as artifacts in CI

- **Developer Experience**
  - Pre-commit hooks with `ruff` for linting
  - Easy-to-extend codebase
  - Clear modular structure (`calculator` module + `tests` folder)

---

## 💡 Why This Project Stands Out

This project is more than just a toy calculator:

- Shows ability to **write clean, testable Python code**
- Demonstrates **professional CI/CD pipeline skills**
- Implements **advanced testing concepts** like BDD, scenario outlines, negative tests
- Shows understanding of **logging, traceability, and observability**
- Perfect portfolio piece for recruiters or future employers to see both **coding** and **engineering best practices**

---

## 🏗 Tech Stack

- Python 3.10 / 3.11
- pytest, pytest-bdd, pytest-cov, pytest-html
- GitHub Actions (CI/CD)
- Ruff for pre-commit linting

---

## 📂 Project Structure

price-calculator/
│
├── calculator/
│   ├── __init__.py
│   ├── price.py
│   └── logging_config.py
│
├── tests/
│   ├── test_price.py          # Unit tests
│   ├── test_price_bdd.py      # BDD step definitions
│   └── features/
│       └── price.feature      # BDD feature file
│
├── .github/
│   └── workflows/
│       └── ci.yml             # CI workflow
│
├── requirements.txt
├── pyproject.toml
├── .pre-commit-config.yaml
└── README.md


---

## ⚡ Quick Start

1. Clone the repo:

```bash
git clone https://github.com/NEMETOM/price-calculator.git
cd price-calculator


2. Install dependencies:

pip install -r requirements.txt
pip install -e .


3. Run all tests

pytest -v


4. Run BDD tests only

pytest tests/test_price_bdd.py --html=report.html --self-contained-html


5. Lint your code

pre-commit run --all-files


### 🔧 Developer Workflow using Makefile

```bash
make install
make test
make coverage
