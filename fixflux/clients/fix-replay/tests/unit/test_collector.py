from fix_replay.collector import collect
from tests.unit.fakes import FakeConsumer, exec_report

P = "RPL-r1-"


class TestCollect:
    def test_counts_acks_and_waits_for_trailing_fills(self, clock):
        consumer = FakeConsumer(
            clock,
            [
                [exec_report(P + "B"), exec_report(P + "S", side="SELL")],
                [],
                [exec_report(P + "B", "F", last_qty=100)],
            ],
        )
        result = collect(consumer, P, 2, timeout_s=60, settle_s=2, clock=clock)

        assert result.acks == 2
        assert [r.exec_type for r in result.reports] == ["0", "0", "F"]
        assert not result.timed_out

    def test_ignores_other_clients_and_other_runs(self, clock):
        consumer = FakeConsumer(
            clock,
            [[exec_report("LIVE1"), exec_report("RPL-other-B"), exec_report(P + "B")]],
        )
        result = collect(consumer, P, 1, timeout_s=60, settle_s=1, clock=clock)
        assert [r.client_id for r in result.reports] == [P + "B"]

    def test_rejected_counts_as_ack(self, clock):
        consumer = FakeConsumer(clock, [[exec_report(P + "B", "8", reason="x")]])
        result = collect(consumer, P, 1, timeout_s=60, settle_s=1, clock=clock)
        assert result.acks == 1 and not result.timed_out

    def test_times_out_when_acks_missing(self, clock):
        consumer = FakeConsumer(clock, [[exec_report(P + "B")]])
        result = collect(consumer, P, 2, timeout_s=5, settle_s=1, clock=clock)
        assert result.timed_out
        assert result.acks == 1

    def test_zero_expected_returns_after_settle(self, clock):
        result = collect(FakeConsumer(clock, []), P, 0, 60, 3, clock=clock)
        assert result.acks == 0 and not result.timed_out
        assert clock.now == 3
