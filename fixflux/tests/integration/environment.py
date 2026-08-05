import json
import os
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy import text

_here = Path(__file__).resolve()
_repo_root = _here.parent.parent.parent  # fixflux/
_trade_store_src = _repo_root / "services" / "trade-store" / "src"
for _p in (str(_repo_root), str(_trade_store_src)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Truncating trades/violations before every scenario gives each one a clean
# slate for test isolation - correct for an ephemeral CI database, but on a
# shared/persistent environment (e.g. a demo Droplet) it silently wipes real
# history between test runs. Default preserves existing behaviour; set
# E2E_TRUNCATE_STATE=false to skip truncation when that matters more than
# isolation for a given run.
_TRUNCATE_STATE = os.getenv("E2E_TRUNCATE_STATE", "true").lower() != "false"


def _start_metrics_server():
    try:
        from prometheus_client import start_http_server
        start_http_server(8005)
    except OSError:
        pass  # port already bound if the test process is reused across runs


def before_all(context):
    if not _TRUNCATE_STATE:
        print(
            "E2E_TRUNCATE_STATE=false: skipping trades/violations truncation "
            "before each scenario - existing history will be preserved."
        )
    _start_metrics_server()
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
    kafka_tags = {
        "needs_kafka",
        "needs_full_stack",
        "needs_risk_service",
        "needs_exec_reports",
    }
    if kafka_tags & set(feature.tags):
        _verify_kafka()
    if "needs_compliance_api" in feature.tags:
        _verify_compliance_api()


def before_scenario(context, scenario):
    if _TRUNCATE_STATE:
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
    if "needs_exec_reports" in all_tags:
        _init_exec_report_consumer(context)


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
    if hasattr(context, "exec_reports_consumer"):
        context.exec_reports_consumer.close()
        del context.exec_reports_consumer
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


def _verify_compliance_api():
    import httpx

    url = os.getenv("COMPLIANCE_URL", "http://localhost:8010")
    try:
        response = httpx.get(f"{url}/health", timeout=5.0)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            "Compliance pipeline tests require compliance-api.\n"
            "Start it with:  docker compose --profile full up compliance-api\n"
            f"Cannot reach {url}/health: {exc}"
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


def _init_exec_report_consumer(context):
    from kafka import KafkaConsumer, TopicPartition

    broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    topic = "execution_reports"
    consumer = KafkaConsumer(
        bootstrap_servers=broker,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=15_000,
    )
    # Manual partition assignment instead of subscribe() + consumer group.
    # This scenario only ever needs one reader with no load-balancing across
    # instances, so there is no reason to depend on (or race against) the
    # JoinGroup/SyncGroup rebalance protocol at all - two rounds of patching
    # around its timing (waiting for consumer.assignment(), then waiting
    # longer) both failed to reliably fix missed messages. assign() takes
    # effect immediately with no rebalance to wait for, and seek_to_end()
    # deterministically positions at each partition's current high-water mark.
    deadline = time.monotonic() + 10
    partition_ids = consumer.partitions_for_topic(topic)
    while not partition_ids and time.monotonic() < deadline:
        partition_ids = consumer.partitions_for_topic(topic)
    if not partition_ids:
        raise RuntimeError(
            f"Could not fetch partition metadata for topic '{topic}' - "
            "is Kafka/Redpanda reachable and is the topic created?"
        )
    topic_partitions = [TopicPartition(topic, p) for p in partition_ids]
    consumer.assign(topic_partitions)
    consumer.seek_to_end(*topic_partitions)
    context.exec_reports_consumer = consumer
    # Holds messages consumed but not matched by an earlier assertion in this
    # scenario - poll() is destructive, so a message for a *later* assertion
    # (e.g. the sell side's Fill, batched together with the buy side's) must be
    # buffered here rather than discarded. See _poll_for_exec_report.
    context.exec_reports_buffer = []
