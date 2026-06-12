from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from routers import upload, jobs, analysis


class Settings(BaseSettings):
    cors_origins: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

app = FastAPI(
    title="Archon API",
    description="Orchestration backend for the Archon financial intelligence platform (Azure)",
    version="1.0.0",
)

_explicit_origins = [o for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit_origins or ["*"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "service": "archon-backend-azure"}
