import contextlib
import io
import json
import re
import shlex
import urllib.error
from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

from fix_replay import cli

# Regex matching: several "I replay ..." steps share a prefix, and parse's
# lazy fields would let the shorter pattern swallow the longer ones.
use_step_matcher("re")

_EXIT_CODES = {
    "ok": cli.EXIT_OK,
    "regression": cli.EXIT_REGRESSION,
    "incomplete": cli.EXIT_INCOMPLETE,
    "preflight": cli.EXIT_PREFLIGHT,
    "error": cli.EXIT_ERROR,
}

# One line per invalid kind, each one that order-service would drop.
_INVALID_LINES = {
    "missing-symbol": "8=FIX.4.2|35=D|49=BAD|54=1|40=2|44=10.0|38=1|",
    "unknown-side": "8=FIX.4.2|35=D|49=BAD|55=AAPL|54=3|40=2|44=10.0|38=1|",
    "zero-price": "8=FIX.4.2|35=D|49=BAD|55=AAPL|54=1|40=2|44=0|38=1|",
    "non-numeric-quantity": "8=FIX.4.2|35=D|49=BAD|55=AAPL|54=1|40=2|44=10|38=abc|",
    "unsupported-type": "8=FIX.4.2|35=G|49=BAD|55=AAPL|54=1|40=2|44=10.0|38=1|",
}

_DEFAULT_ARGS = ["--rate", "0", "--settle", "0", "--timeout", "5"]


def _order_line(client_id: str, symbol: str, side: str, price: str, qty: str) -> str:
    return (
        f"8=FIX.4.2|35=D|49={client_id}|55={symbol}|54={side}|40=2|"
        f"44={price}|38={qty}|"
    )


def _run(context, file: str, run_id: str | None, *extra: str) -> None:
    """Run cli.main with only the I/O boundaries faked: the shared Kafka
    factory's classes and the HTTP call to matching-engine's /metrics."""
    path = context.workdir / file
    lines = context.fix_files[file]
    if lines is not None:  # None: the file deliberately doesn't exist
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    argv = [str(path), *_DEFAULT_ARGS, "--metrics-url", "http://me.test/metrics"]
    if run_id is not None:
        context.out = context.workdir / f"{run_id}.json"
        argv += ["--run-id", run_id, "--out", str(context.out)]
    argv += extra

    pipeline = context.pipeline
    pipeline.reset_book()
    response = MagicMock()
    response.__enter__.return_value.read.return_value = context.metrics_text.encode()
    stdout = io.StringIO()
    with (
        patch("shared.infrastructure.kafka_client.KafkaProducer") as producer_cls,
        patch("shared.infrastructure.kafka_client.KafkaConsumer") as consumer_cls,
        patch("urllib.request.urlopen") as urlopen,
        contextlib.redirect_stdout(stdout),
    ):
        producer_cls.return_value = pipeline.producer
        consumer_cls.return_value = pipeline.consumer
        urlopen.return_value = response
        urlopen.side_effect = context.metrics_error
        # No try/except: every failure must come back as an exit code, so an
        # exception escaping main() fails the scenario.
        context.exit_code = cli.main(argv)
    context.consumer_cls = consumer_cls
    context.stdout = stdout.getvalue()


def _report(context) -> dict:
    return json.loads(context.out.read_text(encoding="utf-8"))


# ── Givens ───────────────────────────────────────────────────────────────────


@given(
    r'a FIX file "(?P<file>[^"]+)" with (?P<buys>\d+) buy and (?P<sells>\d+) sell '
    r'orders for "(?P<symbol>[A-Z]+)" at (?P<price>[\d.]+) for (?P<qty>\d+)'
)
def a_fix_file(context, file, buys, sells, symbol, price, qty):
    lines = [_order_line(f"BUY{i}", symbol, "1", price, qty) for i in range(int(buys))]
    lines += [
        _order_line(f"SELL{i}", symbol, "2", price, qty) for i in range(int(sells))
    ]
    context.fix_files[file] = lines


@given(r'a FIX file "(?P<file>[^"]+)" with only a "(?P<kind>[a-z-]+)" invalid line')
def a_fix_file_without_valid_orders(context, file, kind):
    context.fix_files[file] = [_INVALID_LINES[kind]]


@given(r'the FIX file "(?P<file>[^"]+)" does not exist')
def fix_file_missing(context, file):
    context.fix_files[file] = None


@given(r'the baseline "(?P<name>[^"]+)" does not exist')
def baseline_missing(context, name):
    context.baseline = context.workdir / name


@given(r'the file "(?P<file>[^"]+)" also contains (?P<n>\d+) session messages')
def file_has_session_messages(context, file, n):
    # Heartbeats; the parser counts and skips them.
    context.fix_files[file] += ["8=FIX.4.2|35=0|49=SESSION|"] * int(n)


@given(r'the file "(?P<file>[^"]+)" also contains a "(?P<kind>[a-z-]+)" invalid line')
def file_has_invalid_line(context, file, kind):
    context.fix_files[file].append(_INVALID_LINES[kind])


@given("the pipeline accepts every order")
def pipeline_accepts_every_order(context):
    context.pipeline.rejects.clear()
    context.pipeline.silent = False


@given(
    r'risk-service (?:now )?rejects orders for "(?P<symbol>[A-Z]+)" '
    r'with reason "(?P<reason>[^"]+)"'
)
def risk_service_rejects(context, symbol, reason):
    context.pipeline.rejects[symbol] = reason


@given("the pipeline never acknowledges orders")
def pipeline_is_silent(context):
    context.pipeline.silent = True


@given("the execution_reports topic does not exist")
def reports_topic_missing(context):
    context.pipeline.topic_exists = False


@given(r'matching-engine already has (?P<n>\d+) resting orders on "(?P<symbol>[A-Z]+)"')
def resting_orders(context, n, symbol):
    context.metrics_text += f'orders_in_book{{side="buy",symbol="{symbol}"}} {n}.0\n'


@given("matching-engine's /metrics endpoint is unreachable")
def metrics_unreachable(context):
    context.metrics_error = urllib.error.URLError("connection refused")


@given(
    r'a baseline was recorded by replaying "(?P<file>[^"]+)" '
    r'with run id "(?P<run_id>[^"]+)"'
)
def baseline_recorded(context, file, run_id):
    _run(context, file, run_id)
    assert context.exit_code == cli.EXIT_OK, f"baseline run exited {context.exit_code}"
    context.baseline = context.out


# ── Whens ────────────────────────────────────────────────────────────────────


@when(r'I replay "(?P<file>[^"]+)" as a dry run')
def replay_dry_run(context, file):
    _run(context, file, None, "--dry-run")


@when(r'I replay "(?P<file>[^"]+)" with run id "(?P<run_id>[^"]+)"')
def replay(context, file, run_id):
    _run(context, file, run_id)


@when(
    r'I replay "(?P<file>[^"]+)" with run id "(?P<run_id>[^"]+)" '
    r'and options "(?P<options>[^"]+)"'
)
def replay_with_options(context, file, run_id, options):
    _run(context, file, run_id, *shlex.split(options))


@when(
    r'I replay "(?P<file>[^"]+)" with run id "(?P<run_id>[^"]+)" '
    r"against that baseline"
)
def replay_against_baseline(context, file, run_id):
    _run(context, file, run_id, "--baseline", str(context.baseline))


# ── Thens ────────────────────────────────────────────────────────────────────


@then(r'the replay exits with "(?P<outcome>[a-z]+)"')
def replay_exits_with(context, outcome):
    assert (
        context.exit_code == _EXIT_CODES[outcome]
    ), f"exit code {context.exit_code}, expected {outcome}"


@then("no orders were published to raw_orders")
def nothing_published(context):
    assert context.pipeline.published == [], context.pipeline.published


@then(r"(?P<n>\d+) orders were published to raw_orders")
def n_published(context, n):
    assert len(context.pipeline.published) == int(n), context.pipeline.published


@then("no execution_reports consumer was opened")
def no_consumer(context):
    assert context.consumer_cls.call_count == 0


@then("the execution_reports consumer was closed")
def consumer_closed(context):
    context.pipeline.consumer.close.assert_called_once()


@then(r'every published client_id starts with "(?P<prefix>[^"]+)"')
def client_ids_namespaced(context, prefix):
    ids = [e["client_id"] for e in context.pipeline.published]
    assert ids and all(i.startswith(prefix) for i in ids), ids


@then(
    r"the report summary shows (?P<sent>\d+) sent, (?P<new>\d+) new, "
    r"(?P<rejected>\d+) rejected and (?P<fills>\d+) fills"
)
def report_summary(context, sent, new, rejected, fills):
    summary = _report(context)["summary"]
    actual = [summary[k] for k in ("orders_sent", "new", "rejected", "fills")]
    assert actual == [int(sent), int(new), int(rejected), int(fills)], summary


@then(r"the report's filled quantity is (?P<qty>\d+)")
def report_filled_qty(context, qty):
    assert _report(context)["summary"]["filled_qty"] == int(qty)


@then(
    r"the report shows (?P<session>\d+) session messages skipped "
    r"and (?P<invalid>\d+) invalid lines?"
)
def report_skipped_and_invalid(context, session, invalid):
    summary = _report(context)["summary"]
    assert summary["session_messages_skipped"] == int(session), summary
    assert summary["invalid_lines"] == int(invalid), summary


@then(r'the report lists an invalid line with an error containing "(?P<text>[^"]+)"')
def report_lists_invalid(context, text):
    errors = [line["error"] for line in _report(context)["invalid_lines"]]
    assert any(text in e for e in errors), errors


@then(r'the report counts (?P<n>\d+) rejections with reason "(?P<reason>[^"]+)"')
def report_reject_reasons(context, n, reason):
    assert _report(context)["summary"]["reject_reasons"] == {reason: int(n)}


@then("the report shows 0 acks received and the run timed out")
def report_timed_out(context):
    summary = _report(context)["summary"]
    assert summary["acks_received"] == 0, summary
    assert summary["timed_out"] is True, summary


@then("the baseline diff is empty")
def diff_empty(context):
    assert context.stdout == "", context.stdout


@then(
    r"the baseline diff has (?P<missing>\d+) missing "
    r"and (?P<unexpected>\d+) unexpected executions"
)
def diff_counts(context, missing, unexpected):
    def total(marker: str) -> int:
        return sum(
            int(n)
            for n in re.findall(
                rf"^{re.escape(marker)}\s+x(\d+):", context.stdout, re.MULTILINE
            )
        )

    assert total("- missing") == int(missing), context.stdout
    assert total("+ unexpected") == int(unexpected), context.stdout
