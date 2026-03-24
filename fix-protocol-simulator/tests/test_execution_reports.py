# fix-protocol-simulator/tests/test_execution_reports.py

from fix_simulator.exchange.execution_reports import ExecutionReportFactory


def test_create_returns_fix_message_with_correct_fields():
    report = ExecutionReportFactory.create("ORD001", "2")
    assert report.get("35") == "8"
    assert report.get("37") == "ORD001"
    assert report.get("39") == "2"


def test_create_filled_status():
    report = ExecutionReportFactory.create("ORD002", "2")
    assert report.get("39") == "2"


def test_create_new_status():
    report = ExecutionReportFactory.create("ORD003", "0")
    assert report.get("39") == "0"
