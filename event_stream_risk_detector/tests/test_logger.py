# event_stream_risk_detector/tests/test_logger.py

from event_stream_risk_detector.logger import setup_logger


def test_logger_creation() -> None:
    logger = setup_logger("test_logger")
    assert logger.name == "test_logger"
