"""FastAPI review API (import side-effect free; use create_app / uvicorn --factory)."""

from app.api.main import create_app

__all__ = ["create_app"]
