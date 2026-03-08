# price-calculator/tests/test_config.py

import tempfile

import yaml

from event_stream_risk_detector.config import load_config


def test_load_config_success() -> None:
    data = {"kafka": {"bootstrap": "localhost"}}

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        yaml.dump(data, f)
        path = f.name

    result = load_config(path)

    assert result["kafka"]["bootstrap"] == "localhost"
