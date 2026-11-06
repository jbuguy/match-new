from fastapi import FastAPI

app = FastAPI(
    title="Mahara Match API",
    description="API for the Mahara Match employment support platform.",
    version="0.1.0",
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    """Report that the API process is responsive; does not imply database readiness."""
    return {"status": "ok"}
