import os
from dotenv import load_dotenv

def load_config() -> None:
    load_dotenv()

def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)