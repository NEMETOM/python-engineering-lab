from pydantic import BaseModel

class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9878
    heartbeat_interval: int = 30
    sender_comp_id: str = "EXCHANGE"
    target_comp_id: str = "CLIENT"

settings = Settings()
    