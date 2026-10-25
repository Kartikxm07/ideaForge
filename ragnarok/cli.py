import argparse
import time
import uvicorn
from .api import create_app
from .config import Settings
from .store import Store
from .workflow import run_once


def main() -> None:
    parser = argparse.ArgumentParser(prog="ragnarok")
    parser.add_argument("command", choices=["api", "worker", "migrate", "doctor"])
    parser.add_argument("--once", action="store_true", help="Process at most one step")
    args = parser.parse_args()
    settings = Settings.from_env()
    store = Store(settings.db_path)
    store.migrate()
    if args.command == "api":
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8000)
    elif args.command == "worker":
        while True:
            worked = run_once(store, settings.owner_id)
            if args.once:
                break
            if not worked:
                time.sleep(1)
    elif args.command == "doctor":
        from .model import OllamaProvider
        print({"database": "ok", "ollama": OllamaProvider(settings).health(), "privacy_mode": "local-only"})
    else:
        print("Database migration complete")


if __name__ == "__main__":
    main()
