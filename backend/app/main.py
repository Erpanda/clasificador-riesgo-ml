from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, imports, predictions, reports
from app.core.config import FRONTEND_ORIGIN


app = FastAPI(
    title="API de Riesgo Académico",
    description="Predicción de riesgo académico a partir de variables del ciclo.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

