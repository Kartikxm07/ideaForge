from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import urlparse


def _load_dotenv_if_exists() -> dict[str, str]:
    env_vars = {}
    env_path = Path(".env")
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


@dataclass(frozen=True)
class Settings:
    api_token: str
    owner_id: str
    db_path: Path
    ollama_url: str
    ollama_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        file_env = _load_dotenv_if_exists()
        def get(key: str, default: str = "") -> str:
            return os.getenv(key) or file_env.get(key, default)

        token = get("RAGNAROK_API_TOKEN", "")
        if len(token) < 32 or token == "replace-with-at-least-32-random-characters":
            raise ValueError("RAGNAROK_API_TOKEN must be a private random value of at least 32 characters")
        url = get("RAGNAROK_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password or parsed.path:
            raise ValueError("Ollama URL must be an HTTP loopback origin")
        return cls(
            api_token=token,
            owner_id=get("RAGNAROK_OWNER_ID", "local-owner"),
            db_path=Path(get("RAGNAROK_DB_PATH", "./data/ragnarok.sqlite3")),
            ollama_url=url,
            ollama_model=get("RAGNAROK_OLLAMA_MODEL", "llama3.2"),
        )
