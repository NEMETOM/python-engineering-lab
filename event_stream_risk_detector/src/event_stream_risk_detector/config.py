# src/event_stream_risk_detector/config.py

from pathlib import Path

import yaml


def load_config(path: str = "config.yaml") -> dict:
    config_file = Path(path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
