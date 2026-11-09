from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


RiskStatus = Literal["En riesgo", "Sin riesgo"]


class FactorDetail(BaseModel):
    variable: str
    valor: Any
    cambio_estimado_probabilidad: float
    interpretacion: str


class PredictionResult(BaseModel):
    estudiante_id: str
    datos_entrada: dict[str, Any]
    estado_predicho: RiskStatus
    probabilidad_riesgo: float
    estado_real: RiskStatus | None = None
    factores: list[FactorDetail]
    version_modelo: str
    guardado: bool


class CsvPredictionResponse(BaseModel):
    carga_id: str | None
    total_filas: int
    procesadas: int
    observaciones: list[str]
    resultados: list[PredictionResult]

