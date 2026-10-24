import json
from unittest.mock import MagicMock, patch

import pytest

from fix_replay import cli
from fix_replay.collector import CollectResult
from shared.schemas import ExecutionReportEvent
from tests.unit.fakes import exec_report

ORDERS = (
    "8=FIX.4.2|35=A|49=B|\n"
    "8=FIX.4.2|35=D|49=B|55=AAPL|54=1|40=2|44=175.5|38=100|\n"
    "8=FIX.4.2|35=D|49=S|55=AAPL|54=2|40=2|44=175.5|38=100|\n"
)


@pytest.fixture
def fix_file(tmp_path):
    path = tmp_path / "orders.txt"
    path.write_text(ORDERS)
    return path


def _result(prefix, timed_out=False, fill=True):
    recs = [exec_report(prefix + "B"), exec_report(prefix + "S", side="SELL")]
    if fill:
        recs.append(exec_report(prefix + "B", "F", last_qty=100, last_px=175.5))
    reports = [ExecutionReportEvent(**r.value) for r in recs]
    return CollectResult(reports=reports, acks=2, timed_out=timed_out)


@pytest.fixture
def pipeline():
    """Patch every external boundary of cli.main."""
    with (
        patch("fix_replay.cli.fetch_metrics", return_value="") as metrics,
        patch("fix_replay.cli.create_tail_consumer") as tail,
        patch("fix_replay.cli.create_producer") as producer,
        patch("fix_replay.cli.collect") as collect,
    ):
        collect.side_effect = lambda c, prefix, *a, **k: _result(prefix)
        yield MagicMock(metrics=metrics, tail=tail, producer=producer, collect=collect)


def _run(fix_file, *extra):
    return cli.main([str(fix_file), "--rate", "0", *extra])


class TestMain:
    def test_dry_run_sends_nothing(self, fix_file, pipeline):
        assert _run(fix_file, "--dry-run") == cli.EXIT_OK
        pipeline.producer.assert_not_called()
        pipeline.tail.assert_not_called()

    def test_successful_run_writes_report(self, fix_file, pipeline, tmp_path):
        out = tmp_path / "run.json"
        assert _run(fix_file, "--run-id", "r1", "--out", str(out)) == cli.EXIT_OK
        report = json.loads(out.read_text())
        assert report["client_prefix"] == "RPL-r1-"
        assert report["summary"]["orders_sent"] == 2
        assert report["summary"]["session_messages_skipped"] == 1
        assert pipeline.producer.return_value.send.call_count == 2
        pipeline.tail.return_value.close.assert_called_once()

    def test_tail_consumer_created_before_first_send(self, fix_file, pipeline):
        calls = []

        def tail(*_):
            calls.append("tail")
            return MagicMock()

        pipeline.tail.side_effect = tail
        pipeline.producer.return_value.send.side_effect = lambda *_: calls.append(
            "send"
        )
        _run(fix_file)
        assert calls[0] == "tail"

    def test_incomplete_run_exits_2(self, fix_file, pipeline):
        pipeline.collect.side_effect = lambda c, p, *a, **k: _result(p, True)
        assert _run(fix_file) == cli.EXIT_INCOMPLETE

    def test_matching_baseline_exits_0(self, fix_file, pipeline, tmp_path):
        base = tmp_path / "base.json"
        _run(fix_file, "--run-id", "a", "--out", str(base))
        assert _run(fix_file, "--run-id", "b", "--baseline", str(base)) == cli.EXIT_OK

    def test_diverging_baseline_exits_1(self, fix_file, pipeline, tmp_path, capsys):
        base = tmp_path / "base.json"
        _run(fix_file, "--run-id", "a", "--out", str(base))
        pipeline.collect.side_effect = lambda c, p, *a, **k: _result(p, fill=False)
        code = _run(fix_file, "--run-id", "b", "--baseline", str(base))
        assert code == cli.EXIT_REGRESSION
        assert "- missing" in capsys.readouterr().out


class TestPreflight:
    BOOK = 'orders_in_book{side="buy",symbol="AAPL"} 1.0\n'

    def test_resting_orders_abort(self, fix_file, pipeline):
        pipeline.metrics.return_value = self.BOOK
        assert _run(fix_file) == cli.EXIT_PREFLIGHT
        pipeline.producer.assert_not_called()

    def test_allow_resting_proceeds(self, fix_file, pipeline):
        pipeline.metrics.return_value = self.BOOK
        assert _run(fix_file, "--allow-resting") == cli.EXIT_OK

    def test_unreachable_metrics_proceeds(self, fix_file, pipeline):
        pipeline.metrics.side_effect = OSError("refused")
        assert _run(fix_file) == cli.EXIT_OK
