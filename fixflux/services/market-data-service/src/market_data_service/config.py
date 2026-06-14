import os


class Settings:

    publish_interval = int(os.getenv("PUBLISH_INTERVAL", "10"))


settings = Settings()
