import os
from pathlib import Path
from urllib.parse import quote_plus

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def build_db_url() -> str:
    if env_url := os.getenv("DATABASE_URL"):
        return env_url

    with open(_CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)["database"]

    password = quote_plus(str(cfg["password"]))
    return f"postgresql://{cfg['user']}:{password}@{cfg['host']}:{cfg['port']}/{cfg['name']}"
