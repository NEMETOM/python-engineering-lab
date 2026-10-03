# fixflux/services/fix-gateway/src/fix_gateway/config.py

import os

from pydantic import BaseModel


class Settings(BaseModel):

    host: str = "0.0.0.0"

    port: int = 9878

    buffer_size: int = 4096

    fix_delimiter: str = "|"

    # Real FIX negotiates HeartBtInt (tag 108) per-session at Logon; this simulator
    # uses one fixed timeout for every session instead. Any inbound message resets
    # the timer (matching real FIX session semantics, not just explicit Heartbeat),
    # so a session only expires after this many seconds of total silence.
    heartbeat_timeout_seconds: int = int(
        os.getenv("FIX_HEARTBEAT_TIMEOUT_SECONDS", "60")
    )


settings = Settings()
