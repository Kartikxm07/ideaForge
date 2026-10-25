"""Transactional SQLite storage. All queries include the local owner's scope."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 6:
                raise RuntimeError(f"Unsupported database schema version: {version}")
            if version == 0:
                script = (Path(__file__).resolve().parent / "migrations" / "001_init.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=1")
                version = 1
            if version == 1:
                script = (Path(__file__).resolve().parent / "migrations" / "002_documents.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=2")
                version = 2
            if version == 2:
                script = (Path(__file__).resolve().parent / "migrations" / "003_analysis.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=3")
                version = 3
            if version == 3:
                script = (Path(__file__).resolve().parent / "migrations" / "004_operational_events.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=4")
                version = 4
            if version == 4:
                script = (Path(__file__).resolve().parent / "migrations" / "005_event_import_errors.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=5")
                version = 5
            if version == 5:
                script = (Path(__file__).resolve().parent / "migrations" / "006_odin_state.sql").read_text(encoding="utf-8")
                db.executescript(script)
                db.execute("PRAGMA user_version=6")
                version = 6

    @staticmethod
    def event(db: sqlite3.Connection, task_id: str, owner_id: str, kind: str, message: str) -> None:
        db.execute(
            "INSERT INTO events(task_id,owner_id,type,message,created_at) VALUES(?,?,?,?,?)",
            (task_id, owner_id, kind, message, now()),
        )

    @staticmethod
    def audit(db: sqlite3.Connection, owner_id: str, action: str, resource_id: str, outcome: str) -> None:
        db.execute(
            "INSERT INTO audit_events(owner_id,action,resource_id,outcome,created_at) VALUES(?,?,?,?,?)",
            (owner_id, action, resource_id, outcome, now()),
        )

