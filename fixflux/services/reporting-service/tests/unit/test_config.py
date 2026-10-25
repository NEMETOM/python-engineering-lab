from pathlib import Path
from unittest.mock import patch

from reporting_service import config


class TestLoadReferenceData:
    def test_explicit_path_wins(self, tmp_path):
        path = tmp_path / "ref.yaml"
        path.write_text("participants: {}\ninstruments: {X: {}}\n")
        assert config.load_reference_data(path)["instruments"] == {"X": {}}

    def test_env_var_path(self, tmp_path, monkeypatch):
        path = tmp_path / "ref.yaml"
        path.write_text("instruments: {}\n")
        monkeypatch.setenv("REPORTING_REFERENCE_DATA_PATH", str(path))
        assert config.load_reference_data() == {"instruments": {}}

    def test_docker_path_used_when_present(self, tmp_path, monkeypatch):
        monkeypatch.delenv("REPORTING_REFERENCE_DATA_PATH", raising=False)
        path = tmp_path / "ref.yaml"
        path.write_text("instruments: {D: {}}\n")
        with patch.object(config, "_DOCKER_DEFAULT", path):
            assert "D" in config.load_reference_data()["instruments"]

    def test_falls_back_to_source_tree_file(self, monkeypatch):
        monkeypatch.delenv("REPORTING_REFERENCE_DATA_PATH", raising=False)
        with patch.object(config, "_DOCKER_DEFAULT", Path("/nonexistent")):
            data = config.load_reference_data()
        assert {"AAPL", "MSFT", "EURUSD"} <= set(data["instruments"])


class TestDefaults:
    def test_deadline_is_one_minute(self):
        assert config.PUBLICATION_DEADLINE_SECONDS == 60

    def test_topic_and_group(self):
        assert (config.INPUT_TOPIC, config.GROUP_ID) == ("trades", "reporting-service")
