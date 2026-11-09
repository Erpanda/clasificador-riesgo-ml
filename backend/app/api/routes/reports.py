from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.report_service import build_csv, build_pdf


router = APIRouter(prefix="/reports", tags=["reportes"])


class ReportRequest(BaseModel):
    carga_id: str | None = None
    resultados: list[dict[str, Any]] = Field(min_length=1, max_length=5000)


@router.post("/csv")
def download_csv(request: ReportRequest) -> Response:
    return Response(
        content=build_csv(request.resultados),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="clasificacion_riesgo.csv"'},
    )


@router.post("/pdf")
def download_pdf(request: ReportRequest) -> Response:
    return Response(
        content=build_pdf(request.resultados, request.carga_id),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_riesgo_academico.pdf"'},
    )

