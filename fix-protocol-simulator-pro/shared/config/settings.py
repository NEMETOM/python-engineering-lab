import os

from shared.config._loader import build_db_url


class Settings:

    kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")

    db_url = build_db_url()

    log_level = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
