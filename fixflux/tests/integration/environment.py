import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import text

_here = Path(__file__).resolve()
_repo_root = _here.parent.parent.parent  # fixflux/
_trade_store_src = _repo_root / "services" / "trade-store" / "src"
for _p in (str(_repo_root), str(_trade_store_src)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def before_all(context):
    from shared.infrastructure.db import Base, engine
    from trade_store.models import TradeModel  # noqa: F401 - registers with Base

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            "Integration tests require PostgreSQL.\n"
            "Start it with:  docker-compose up postgres\n"
            f"Error: {exc}"
        ) from exc

    Base.metadata.create_all(bind=engine)

    from fastapi.testclient import TestClient
    from trade_store.api.main import create_app

    context.api_client = TestClient(create_app())


def before_feature(context, feature):
    kafka_tags = {"needs_kafka", "needs_full_stack", "needs_risk_service"}
    if kafka_tags & set(feature.tags):
        _verify_kafka()


def before_scenario(context, scenario):
    _truncate_trades()
    _truncate_violations()
    # Fresh client ID per scenario so unmatched orders from TradeSizeRule
    # scenarios don't accumulate in the risk-service's in-memory PositionStore
    # across runs and eventually hit RISK_MAX_OPEN_ORDERS=10.
    context.e2e_client_id = f"E2E_{uuid.uuid4().hex[:8].upper()}"
    all_tags = set(scenario.tags) | set(scenario.feature.tags)
    if "needs_kafka" in all_tags:
        _init_kafka_consumer(context)
    if "needs_risk_service" in all_tags:
        _init_risk_consumers(context)


def after_scenario(context, scenario):
    if hasattr(context, "kafka_consumer"):
        context.kafka_consumer.close()
        del context.kafka_consumer
    if hasattr(context, "risk_approved_consumer"):
        context.risk_approved_consumer.close()
        del context.risk_approved_consumer
    if hasattr(context, "risk_rejected_consumer"):
        context.risk_rejected_consumer.close()
        del context.risk_rejected_consumer
    _restart_chaos_services(context)


def _restart_chaos_services(context):
    """Restart any containers left stopped by a chaos scenario that failed mid-way."""
    import subprocess

    stopped = getattr(context, "chaos_stopped_services", set())
    if not stopped:
        return
    compose_dir = Path(__file__).resolve().parent.parent.parent
    for service in list(stopped):
        subprocess.run(
            ["docker", "compose", "start", service],
            cwd=str(compose_dir),
            capture_output=True,
        )
    context.chaos_stopped_services.clear()


def _truncate_trades():
    from shared.infrastructure.db import SessionLocal
    from trade_store.models import TradeModel

    session = SessionLocal()
    try:
        session.query(TradeModel).delete()
        session.commit()
    finally:
        session.close()


def _truncate_violations():
    from shared.infrastructure.db import SessionLocal

    session = SessionLocal()
    try:
        session.execute(text("DELETE FROM compliance_violations"))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _verify_kafka():
    import socket

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    host, port = broker.rsplit(":", 1)
    try:
        with socket.create_connection((host, int(port)), timeout=5):
            pass
    except Exception as exc:
        raise RuntimeError(
            "Kafka pipeline tests require Kafka.\n"
            "Start it with:  docker-compose up redpanda\n"
            f"Cannot reach {broker}: {exc}"
        ) from exc


def _init_kafka_consumer(context):
    from kafka import KafkaConsumer

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    consumer = KafkaConsumer(
        "trades",
        bootstrap_servers=broker,
        # Unique group so this consumer always starts from the position
        # established by the initial poll below, not a committed offset.
        group_id=f"int-test-{uuid.uuid4().hex}",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=15_000,
        session_timeout_ms=10_000,
    )
    # Prime partition assignment so the consumer is positioned at the current
    # end of the topic BEFORE the scenario publishes any messages.
    consumer.poll(timeout_ms=2_000)
    context.kafka_consumer = consumer


def _init_risk_consumers(context):
    from kafka import KafkaConsumer

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")

    def _make(topic):
        c = KafkaConsumer(
            topic,
            bootstrap_servers=broker,
            group_id=f"int-risk-{uuid.uuid4().hex}",
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=15_000,
            session_timeout_ms=10_000,
        )
        c.poll(timeout_ms=2_000)
        return c

    context.risk_approved_consumer = _make("risk_approved_orders")
    context.risk_rejected_consumer = _make("risk_rejected_orders")
