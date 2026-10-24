from fix_replay.collector import CollectResult
from fix_replay.parser import ParsedFiles, ReplayOrder
from fix_replay.report import build_report, compare, fingerprint
from shared.schemas import ExecutionReportEvent
from tests.unit.fakes import exec_report

P = "RPL-r1-"


def _reports(*recs):
    return [ExecutionReportEvent(**r.value) for r in recs]


class TestFingerprint:
    def test_strips_prefix_and_volatile_ids_and_sorts(self):
        a = _reports(
            exec_report(P + "S", side="SELL", order_id="o2"),
            exec_report(P + "B", order_id="o1"),
        )
        b = _reports(
            exec_report("RPL-r2-B", order_id="zz"),
            exec_report("RPL-r2-S", side="SELL", order_id="yy"),
        )
        fa, fb = fingerprint(a, P), fingerprint(b, "RPL-r2-")
        assert fa == fb
        assert fa[0]["client_id"] == "B"
        assert "order_id" not in fa[0] and "exec_id" not in fa[0]


class TestBuildReport:
    def test_summary_counts(self):
        parsed = ParsedFiles(
            orders=[ReplayOrder("f:1", "B", "AAPL", "BUY", 1.0, 1)] * 3,
            session_messages=2,
            invalid=[{"source": "f:9", "raw": "x", "error": "e"}],
        )
        result = CollectResult(
            reports=_reports(
                exec_report(P + "B"),
                exec_report(P + "S", side="SELL"),
                exec_report(P + "X", "8", reason="notional too big"),
                exec_report(P + "B", "F", last_qty=60, last_px=175.5),
                exec_report(P + "S", "F", side="SELL", last_qty=60, last_px=175.5),
            ),
            acks=3,
        )
        report = build_report("r1", P, ["f"], parsed, result)
        assert report["summary"] == {
            "orders_sent": 3,
            "session_messages_skipped": 2,
            "invalid_lines": 1,
            "acks_received": 3,
            "timed_out": False,
            "new": 2,
            "rejected": 1,
            "fills": 2,
            "filled_qty": 120,
            "reject_reasons": {"notional too big": 1},
        }
        assert len(report["executions"]) == 5


class TestCompare:
    def test_identical_runs_have_no_diff(self):
        rows = [{"client_id": "B", "exec_type": "0"}]
        assert compare({"executions": rows}, {"executions": list(rows)}) == []

    def test_reports_missing_and_unexpected_with_multiplicity(self):
        fill = {"client_id": "B", "exec_type": "F"}
        rej = {"client_id": "B", "exec_type": "8"}
        diff = compare({"executions": [fill, fill]}, {"executions": [fill, rej]})
        assert len(diff) == 2
        assert diff[0].startswith("- missing   x1:") and '"F"' in diff[0]
        assert diff[1].startswith("+ unexpected x1:") and '"8"' in diff[1]
