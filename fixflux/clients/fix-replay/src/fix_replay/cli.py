import argparse
import json
import sys
import uuid
from pathlib import Path

from fix_replay import config
from fix_replay.collector import collect
from fix_replay.parser import load_files
from fix_replay.preflight import fetch_metrics, resting_orders
from fix_replay.replayer import Replayer
from fix_replay.report import build_report, compare
from shared.infrastructure.kafka_client import create_producer, create_tail_consumer
from shared.observability.log_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_INCOMPLETE = 2
EXIT_PREFLIGHT = 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fix-replay",
        description="Replay FIX message files through the live FixFlux pipeline "
        "and capture the resulting execution reports.",
    )
    p.add_argument("files", nargs="+", type=Path, help="FIX files, replayed in order")
    p.add_argument("--run-id", default=None, help="default: random 8-char hex")
    p.add_argument(
        "--rate",
        type=float,
        default=config.DEFAULT_RATE,
        help="orders/second; 0 = unthrottled (default: %(default)s)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=config.DEFAULT_TIMEOUT_S,
        help="max seconds to wait for acks (default: %(default)s)",
    )
    p.add_argument(
        "--settle",
        type=float,
        default=config.DEFAULT_SETTLE_S,
        help="quiet seconds after last report before stopping "
        "(default: %(default)s)",
    )
    p.add_argument("--out", type=Path, help="write the JSON run report here")
    p.add_argument(
        "--baseline",
        type=Path,
        help="compare against a previous --out report; exit 1 on diff",
    )
    p.add_argument(
        "--metrics-url",
        default=config.MATCHING_ENGINE_METRICS_URL,
        help="matching-engine /metrics, for the resting-order check",
    )
    p.add_argument(
        "--allow-resting",
        action="store_true",
        help="replay even if the book already holds resting orders "
        "on the replayed symbols",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="parse and validate only; send nothing"
    )
    return p


def _preflight(url: str, symbols: set[str], allow_resting: bool) -> bool:
    try:
        resting = resting_orders(fetch_metrics(url), symbols)
    except OSError as exc:
        logger.warning(f"resting-order check skipped, {url} unreachable: {exc}")
        return True
    if not resting:
        return True
    msg = (
        f"matching-engine already has resting orders on replayed symbols {resting}; "
        "replayed orders can match against them, so results will not be "
        "reproducible"
    )
    if allow_resting:
        logger.warning(msg)
        return True
    logger.error(f"{msg}. Reset the pipeline or pass --allow-resting.")
    return False


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_id = args.run_id or uuid.uuid4().hex[:8]
    prefix = config.client_prefix(run_id)

    parsed = load_files(args.files)
    for bad in parsed.invalid:
        logger.warning(f"invalid line {bad['source']}: {bad['error']}")
    logger.info(
        f"replay_plan | run={run_id} orders={len(parsed.orders)} "
        f"session_skipped={parsed.session_messages} invalid={len(parsed.invalid)}"
    )
    if args.dry_run:
        return EXIT_OK

    symbols = {o.symbol for o in parsed.orders}
    if not _preflight(args.metrics_url, symbols, args.allow_resting):
        return EXIT_PREFLIGHT

    # Tail consumer first: it must be positioned before the first send.
    consumer = create_tail_consumer(config.REPORTS_TOPIC)
    try:
        Replayer(create_producer(), prefix, args.rate).send(parsed.orders)
        result = collect(
            consumer, prefix, len(parsed.orders), args.timeout, args.settle
        )
    finally:
        consumer.close()

    report = build_report(run_id, prefix, [str(f) for f in args.files], parsed, result)
    summary = report["summary"]
    logger.info(
        f"replay_result | run={run_id} sent={summary['orders_sent']} "
        f"acks={summary['acks_received']} new={summary['new']} "
        f"rejected={summary['rejected']} fills={summary['fills']} "
        f"timed_out={summary['timed_out']}"
    )
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str) + "\n")
        logger.info(f"report written to {args.out}")

    if result.timed_out:
        logger.error(
            f"only {result.acks}/{len(parsed.orders)} orders acked within "
            f"{args.timeout}s"
        )
        return EXIT_INCOMPLETE

    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        diff = compare(baseline, report)
        if diff:
            print("\n".join(diff), file=sys.stdout)
            logger.error(f"regression: {len(diff)} execution difference(s)")
            return EXIT_REGRESSION
        logger.info("no regression against baseline")

    return EXIT_OK
