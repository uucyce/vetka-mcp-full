"""
TaskBoard Agent Gateway — FastAPI Application

Run with:
    uvicorn src.app:app --host 0.0.0.0 --port 5001

@license MIT
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router as gateway_router
from .routes_admin import router as gateway_admin_router
from .audit import AuditMiddleware

app = FastAPI(
    title="TaskBoard Agent Gateway",
    description="REST API for external AI agents to work with TaskBoard",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging
app.add_middleware(AuditMiddleware)

# Routes
app.include_router(gateway_router)
app.include_router(gateway_admin_router)


@app.get("/")
async def root():
    return {
        "service": "taskboard-agent-gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/gateway/health",
    }
