"""
API endpoints for RAGNAROK / ODIN.
"""
from ragnarok.api import create_app
from ragnarok.config import Settings
from ragnarok.store import Store

def get_app():
    return create_app()

app = create_app()

__all__ = ["create_app", "get_app", "app"]
