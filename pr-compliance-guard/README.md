### 📘 pr-compliance-guard
PR Compliance Guard

A lightweight, configurable compliance engine that validates Pull Requests against organizational rules (branch naming, commit hygiene, Jira references) — designed to run locally or in CI pipelines.


### 🚀 Why This Project Exists

Modern engineering teams need guardrails:
- Enforce branch naming conventions
- Prevent forbidden commit messages (e.g. WIP, fixup)
- Ensure PR titles reference Jira tickets
- Automatically fail non-compliant Pull Requests

This project simulates a real-world DevOps compliance layer that can run:
- Locally via CLI
- In GitHub Actions
- Inside Docker
- As part of a CI governance workflow

It demonstrates:
- Clean architecture
- Config-driven validation
- BDD testing
- CI/CD automation
- Production-style packaging

### 🏗 Architecture

pr-compliance-guard/
│
├── compliance/
│   ├── engine.py        # Core compliance logic
│   ├── rules.py         # Rule validation functions
│   ├── config.py        # YAML config loader
│   └── __main__.py      # CLI entrypoint
│
├── config/
│   ├── default.yaml
│   └── relaxed.yaml
│
├── tests/
|   |── data/
|   |    ├── invalid_pr.json
|   |    └── valid_pr.json 
|   |
│   ├── test_engine.py
│   ├── test_compliance_bdd.py
│   └── features/
│       └── compliance.feature
│
└── Dockerfile


### ⚙️ How It Works
The ComplianceEngine evaluates:

| Rule     | What It Validates                    |
| -------- | ------------------------------------ |
| Branch   | Matches configured regex             |
| Commit   | No forbidden words                   |
| PR Title | Contains Jira ticket (optional rule) |

The result:
{
  "branch": true,
  "commit": true,
  "jira": true,
  "compliant": true
}


### 📦 Installation

pip install -r requirements.txt
pip install -e .


### 🖥 CLI Usage

python -m compliance \
  --config config/default.yaml \
  --input tests/data/valid_pr.json

Example output:
{
  "branch": true,
  "commit": true,
  "jira": true,
  "compliant": true
}  


### 🧪 Running Tests

Unit tests
pytest tests/test_engine.py --cov=compliance

BDD tests
pytest tests/test_compliance_bdd.py


Feature: PR Compliance

  Scenario: Valid PR
    Given branch "feature/COM-123-add-check"
    And commit message "COM-123 add validation"
    And PR title "COM-123 Add validation"
    When compliance is evaluated
    Then result should be compliant


### 🐳 Docker Support

docker build -t pr-compliance-guard .

Run:
docker run --rm pr-compliance-guard \
  --config config/default.yaml \
  --input tests/data/valid_pr.json


### 🔁 GitHub Actions Integration

The project is designed to:
- Run unit tests on push
- Run BDD tests on pull request
- Enforce coverage thresholds
- Fail PRs automatically if compliance fails
This mirrors enterprise CI governance practices.


### 📊 Engineering Concepts Demonstrated

- Regex-based validation
- Config-driven architecture (YAML)
- CLI design with argument parsing
- JSON structured output
- BDD with pytest-bdd
- Unit + BDD test separation
- CI conditional jobs
- Docker packaging
- Coverage enforcement
- PR-level automation


### 💼 Recruiter / Hiring Manager Note

This project simulates a real-world DevOps compliance tool that enforces pull request standards via configurable rules, automated testing, and CI integration.

It demonstrates:
- Clean modular architecture
- Configuration-driven design
- CI/CD pipeline orchestration
- Test layering (unit + BDD)
- Production-style packaging and Dockerization


### 🧠 Future Improvements (Roadmap Ideas)

- GitHub API integration to comment on PRs
- Auto-failing PRs via exit codes
- Plugin-based rule system
- Slack / Teams notification integration
- Correlation IDs for structured logging
- JSON schema validation
- Multi-repo governance support


### 👨‍💻 Author

Built as part of the Python Engineering Lab — a weekly mini engineering project series focused on production-ready patterns and CI-driven design.
