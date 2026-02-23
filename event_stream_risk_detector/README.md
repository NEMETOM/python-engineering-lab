### Event Stream Risk Detector

A mid-level streaming project that demonstrates real-time transaction risk detection using Apache Kafka, clean architecture, Docker, CI, unit testing, and BDD.

This project simulates a risk detection microservice that consumes transaction events from Kafka and flags high-risk activity based on configurable business rules.


### 🚀 Project Goals

This project demonstrates:
- Event-driven architecture
- Kafka consumer design
- Business rule engine
- Dockerized microservice
- Unit testing
- BDD testing (pytest-bdd)
- CI with GitHub Actions
- Coverage enforcement
- Professional src layout
- Clean separation of concerns

This is designed as a mid-level streaming backend project, suitable for backend, data engineering, or platform engineering roles.


### 🏗️ Architecture

Kafka Producer → Kafka Topic → Risk Detector Consumer → Risk Evaluation

The service:
- Consumes transaction events from Kafka
- Applies rule-based risk evaluation
- Flags high-value or suspicious transactions
- Logs evaluation results


### 📂 Project Structure

event_stream_risk_detector/
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── README.md
│
├── src/
│   └── event_stream_risk_detector/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── consumer.py            # Kafka consumer service
│       ├── producer.py            # Kafka producer utility
│       ├── risk_evaluator.py      # Core risk evaluation logic
│       ├── rules.py               # Business risk rules
│       ├── schema.py              # Event schema / validation
│       ├── logger.py              # Logger wrapper (if used)
│       └── logging_config.py      # Structured JSON logging config
│
└── tests/
    ├── test_rules.py              # Unit tests for business rules
    ├── test_customer_bdd.py       # BDD scenarios for risk logic
    └── features/
        └── risk.feature           # Gherkin feature definitions


### 🧠 Business Logic

Example transaction event:
{
  "user_id": 123,
  "amount": 15000,
  "country": "UK"
}

The risk engine evaluates:
- High-value transactions
- Suspicious thresholds
- Rule-based decision logic

Example output:
{
  "high_value": true,
  "risk_score": 0.92
}


### 🐍 Installation (Local)

1️⃣ Clone repository

git clone <your-repo-url>
cd python-engineering-lab/event_stream_risk_detector

2️⃣ Install dependencies

pip install -r requirements.txt
pip install -e .

### 🧪 Running Tests

Run all tests in tests/:
python -m pytest tests -v

Run a specific test file:
python -m pytest tests/test_customer_bdd.py -v

Run with coverage:
python -m pytest --cov=src --cov-report=term-missing


### 🐳 Running with Docker (Kafka Environment)
This project includes a full Kafka environment using Docker Compose.

Start everything:
docker compose up --build

This starts:
- Zookeeper
- Kafka broker
- Risk detector service


### 📨 Producing Test Events
To manually produce events:

1️⃣ Enter Kafka container:
docker exec -it <kafka_container_id> bash

2️⃣ Start producer
kafka-console-producer \
  --broker-list kafka:9092 \
  --topic transactions

3️⃣ Send test event
{"user_id": 1, "amount": 20000, "country": "UK"}  
The consumer will evaluate and log the result.

Run producer as a module:

# Install package in editable mode
cd event_stream_risk_detector
python -m pip install -e .

# Run the producer
python -m event_stream_risk_detector.producer


### 🔁 CI Pipeline
The GitHub Actions workflow runs:
- Unit tests
- BDD tests
- Coverage validation
- Manual trigger support (workflow_dispatch)
- Push trigger (main branch)
- Pull request trigger
This ensures code quality and prevents regressions.


### 🧩 Technologies Used

Python 3.12
Apache Kafka
Docker
Docker Compose
pytest
pytest-bdd
GitHub Actions
Clean architecture principles


### 📦 Example CLI Usage (If Implemented)
If a CLI entrypoint is defined:
python -m event_stream_risk_detector.consumer


### 🧪 Testing Strategy
This project uses two testing layers:

Unit Tests
- Test pure business logic (risk engine)
- No Kafka dependency
- Fast and isolated

BDD Tests
- Validate business behavior
- Human-readable Gherkin scenarios
- Verify rule expectations

This mimics real enterprise test layering.


### 🔮 Possible Future Improvements

- Async Kafka consumer (aiokafka)
- Dead-letter topic
- Retry strategy
- Exactly-once semantics
- Structured JSON logging
- Prometheus metrics
- Schema Registry (Avro)
- Idempotent processing
- Event enrichment
- Risk model upgrade (ML-based scoring)


### 💼 What This Project Demonstrates
This is not a toy project.

It demonstrates:
- Event-driven microservice design
- Kafka integration
- Clean modular Python packaging
- Test-driven development
- CI/CD enforcement
- Dockerized infrastructure
- Professional engineering standards

Suitable for:
- Backend Engineer
- Data Engineer
- Platform Engineer
- SDET / Automation Engineer
- Streaming Engineer


### 🧠 Why This Matters
Modern systems are event-driven.
- Building Kafka-based services demonstrates:
- Distributed systems awareness
- Asynchronous architecture understanding
- Production-readiness mindset
- Scalability thinking
This is exactly the type of project that stands out in interviews.


### 👤 Author
Built as part of the Python Engineering Lab project portfolio.