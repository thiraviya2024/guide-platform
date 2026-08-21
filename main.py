"""Compatibility entrypoint for local development.

The canonical application lives in :mod:`app.main`; re-exporting it keeps
``uvicorn main:app`` consistent with the deployment entrypoint.
"""

from app.main import app

__all__ = ["app"]
