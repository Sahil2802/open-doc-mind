"""ASGI entrypoint for deployment platforms and local execution."""

import os

import uvicorn

from backend.api.main import app


if __name__ == "__main__":
    # Render exposes the desired bind port via PORT.
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
