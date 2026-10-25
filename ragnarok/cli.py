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
    parser.add_argument("command", choices=["api", "worker", "migrate", "doctor", "ingest-odin", "ingest-events"])
    parser.add_argument("--once", action="store_true", help="Process at most one step")
    parser.add_argument("--bundle", type=Path, help="Explicit path to Odin bundle for ingest-odin")
    parser.add_argument("--file", type=Path, help="JSONL event drop for ingest-events")
    args = parser.parse_args()
    settings = Settings.from_env()
    store = Store(settings.db_path)
    store.migrate()
    if args.command == "api":
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8000)
    elif args.command == "worker":
        from .analysis import run_analysis_once
        from .model import OllamaProvider
        provider = OllamaProvider(settings)
        print(f"[Ragnarok Worker] Started. Listening on {settings.db_path} (owner: {settings.owner_id}, model: {settings.model_heavy})")
        print("[Ragnarok Worker] Polling for tasks from API... (Press Ctrl+C to stop)")
        try:
            while True:
                worked = run_once(store, settings.owner_id)
                if not worked:
                    worked = run_analysis_once(store, settings.owner_id, provider)
                if worked:
                    print(f"[Ragnarok Worker] Processed job successfully at {time.strftime('%H:%M:%S')}")
                if args.once:
                    break
                if not worked:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Ragnarok Worker] Stopped by user.")
    elif args.command == "doctor":
        from .model import OllamaProvider
        print({"database": "ok", "ollama": OllamaProvider(settings).health(), "privacy_mode": "local-only"})
    elif args.command == "ingest-odin":
        from .documents import import_odin_bundle
        if args.bundle is None:
            parser.error("ingest-odin requires --bundle")
        imported = import_odin_bundle(store, settings.owner_id, args.bundle)
        print(f"Imported {len(imported)} text documents")
    elif args.command == "ingest-events":
        from .operational_events import import_event_drop
        if args.file is None:
            parser.error("ingest-events requires --file")
        print(import_event_drop(store, settings.owner_id, args.file))
    else:
        print("Database migration complete")


if __name__ == "__main__":
    main()
