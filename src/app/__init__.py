"""`src.app` package entrypoint.

This file makes `src.app` a regular package and helps imports like `from src.db.db import ...`
work consistently when running the application as a module or via the `python -m` flag.
"""

__all__ = ["app"]
