# src/event_stream_risk_detector/config.py

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    config_file = Path(path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a dictionary")

    return data
