"""Minimal FastAPI app for deployment smoke testing on Render."""

from fastapi import FastAPI

app = FastAPI(title="RAG Smoke App", version="1.0.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "smoke app running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "smoke"}
