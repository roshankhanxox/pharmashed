"""FastAPI application entrypoint (M16)."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # load .env from cwd or any parent directory

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pharmashed_api.routes import assistant, community, core, fhir, scenario

app = FastAPI(
    title="PharmaShed API",
    description="Sampling-priority screening for pharmaceuticals in urban streams.",
    version="0.1.0",
)

import os

_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://pharmashed.roshankhan.me",
]
if extra := os.getenv("CORS_ORIGINS"):
    _origins.extend(o.strip() for o in extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(core.router, prefix="/api")
app.include_router(scenario.router, prefix="/api")
app.include_router(fhir.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(community.router, prefix="/api")
