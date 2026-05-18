# fix-protocol-simulator-pro/services/fix-gateway/src/fix_gateway/config.py

from pydantic import BaseModel


class Settings(BaseModel):

    host: str = "0.0.0.0"

    port: int = 9878

    buffer_size: int = 4096

    fix_delimiter: str = "|"


settings = Settings()
