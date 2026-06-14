import os


class Settings:

    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9092")

    db_url = os.getenv(
        "DATABASE_URL", "postgresql://user:password@postgres:5432/trades"
    )


settings = Settings()
