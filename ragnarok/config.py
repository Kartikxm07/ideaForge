from dataclasses import dataclass
from pathlib import Path
import os


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
    anthropic_api_key: str
    model_heavy: str
    model_light: str = "claude-haiku-4-5"
    openrouter_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = ""
    odin_alert_recipient: str = ""
    thor_sepolia_rpc_url: str = ""
    thor_testnet_private_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        file_env = _load_dotenv_if_exists()

        def get(key: str, default: str = "") -> str:
            return os.getenv(key) or file_env.get(key, default)

        token = get("RAGNAROK_API_TOKEN", "")
        if len(token) < 32 or token == "replace-with-at-least-32-random-characters":
            raise ValueError("RAGNAROK_API_TOKEN must be a private random value of at least 32 characters")

        return cls(
            api_token=token,
            owner_id=get("RAGNAROK_OWNER_ID", "local-owner"),
            db_path=Path(get("RAGNAROK_DB_PATH", "./data/ragnarok.sqlite3")),
            anthropic_api_key=get("ANTHROPIC_API_KEY", ""),
            model_heavy=get("MODEL_HEAVY", "openai/gpt-oss-120b" if get("OPENROUTER_API_KEY") else "claude-sonnet-4-5"),
            model_light=get("MODEL_LIGHT", "openai/gpt-oss-120b" if get("OPENROUTER_API_KEY") else "claude-haiku-4-5"),
            openrouter_api_key=get("OPENROUTER_API_KEY", ""),
            resend_api_key=get("RESEND_API_KEY", ""),
            resend_from_email=get("RESEND_FROM_EMAIL", ""),
            odin_alert_recipient=get("ODIN_ALERT_RECIPIENT", ""),
            thor_sepolia_rpc_url=get("THOR_SEPOLIA_RPC_URL", ""),
            thor_testnet_private_key=get("THOR_TESTNET_PRIVATE_KEY", ""),
        )
