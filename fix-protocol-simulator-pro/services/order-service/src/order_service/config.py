import os


class Settings:

    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9092")


settings = Settings()
