import argparse
import time
from pathlib import Path
import uvicorn
from .api import create_app
from .config import Settings
from .store import Store
from .workflow import run_once


def main() -> None:
    parser = argparse.ArgumentParser(prog="ragnarok")
    parser.add_argument("command", choices=["api", "worker", "migrate", "doctor", "ingest-odin"])
    parser.add_argument("--once", action="store_true", help="Process at most one step")
    parser.add_argument("--bundle", type=Path, help="Explicit path to Odin bundle for ingest-odin")
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
    elif args.command == "ingest-odin":
        from .documents import import_odin_bundle
        if args.bundle is None:
            parser.error("ingest-odin requires --bundle")
        imported = import_odin_bundle(store, settings.owner_id, args.bundle)
        print(f"Imported {len(imported)} text documents")
    else:
        print("Database migration complete")


if __name__ == "__main__":
    main()
