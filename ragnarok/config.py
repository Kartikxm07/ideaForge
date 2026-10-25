from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    api_token: str
    owner_id: str
    db_path: Path
    ollama_url: str
    ollama_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("RAGNAROK_API_TOKEN", "")
        if len(token) < 32 or token == "replace-with-at-least-32-random-characters":
            raise ValueError("RAGNAROK_API_TOKEN must be a private random value of at least 32 characters")
        url = os.getenv("RAGNAROK_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password or parsed.path:
            raise ValueError("Ollama URL must be an HTTP loopback origin")
        return cls(
            api_token=token,
            owner_id=os.getenv("RAGNAROK_OWNER_ID", "local-owner"),
            db_path=Path(os.getenv("RAGNAROK_DB_PATH", "./data/ragnarok.sqlite3")),
            ollama_url=url,
            ollama_model=os.getenv("RAGNAROK_OLLAMA_MODEL", "llama3.2"),
        )
