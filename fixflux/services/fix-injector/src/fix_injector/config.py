import os


class Settings:

    target_topic = os.getenv("FIX_INJECTOR_TARGET_TOPIC", "raw_orders")


settings = Settings()
