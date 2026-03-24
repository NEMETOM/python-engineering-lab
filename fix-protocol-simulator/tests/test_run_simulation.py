# fix-protocol-simulator/tests/test_run_simulation.py

from unittest.mock import MagicMock, patch

from fix_simulator.simulation.run_simulation import run


def test_run_starts_fix_server(monkeypatch):
    mock_server = MagicMock()

    with patch(
        "fix_simulator.simulation.run_simulation.setup_logger"
    ) as mock_logger, patch(
        "fix_simulator.simulation.run_simulation.FixServer", return_value=mock_server
    ) as mock_cls, patch(
        "fix_simulator.simulation.run_simulation.asyncio.run"
    ) as mock_asyncio_run:

        run()

        mock_logger.assert_called_once()
        mock_cls.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_server.start())
