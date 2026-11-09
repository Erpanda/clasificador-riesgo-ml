from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import MAX_UPLOAD_MB
from app.schemas.prediction import CsvPredictionResponse, PredictionResult
from app.schemas.student import StudentFeatures
from app.services.csv_service import parse_csv
from app.services.database_service import save_batch
from app.services.model_service import ModelNotReadyError, model_version, predict_one


router = APIRouter(prefix="/imports", tags=["cargas CSV"])
logger = logging.getLogger(__name__)


@router.post("/csv", response_model=CsvPredictionResponse)
async def predict_csv(file: UploadFile = File(...)) -> CsvPredictionResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Sube un archivo con extensión .csv.")
    raw = await file.read((MAX_UPLOAD_MB * 1024 * 1024) + 1)
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"El archivo supera el límite de {MAX_UPLOAD_MB} MB.")
    try:
        rows, observations, _ = parse_csv(raw)
        response_rows: list[PredictionResult] = []
        persistence_rows: list[dict] = []
        persistence_predictions: list[dict] = []
        for row in rows:
            label, probability, factors = predict_one(row["features"])
            result = PredictionResult(
                estudiante_id=row["estudiante_id"],
                datos_entrada={
                    key: (None if pd.isna(value) else value)
                    for key, value in row["source_features"].items()
                },
                estado_predicho=label,
                probabilidad_riesgo=round(probability, 4),
                estado_real=row["estado_real"],
                factores=factors,
                version_modelo=model_version(),
                guardado=False,
            )
            response_rows.append(result)
            feature_values = {
                name: (None if pd.isna(value) else value)
                for name, value in row["source_features"].items()
            }
            persistence_rows.append({
                "estudiante_id": row["estudiante_id"],
                "features": feature_values,
                "estado_real": row["estado_real"],
            })
            persistence_predictions.append({
                "estado_predicho": label,
                "probabilidad_riesgo": round(probability, 4),
                "version_modelo": model_version(),
                "factores": [item.model_dump() for item in factors],
            })
        batch_id = save_batch(file.filename, persistence_rows, persistence_predictions)
        for item in response_rows:
            item.guardado = batch_id is not None
        return CsvPredictionResponse(
            carga_id=batch_id,
            total_filas=len(response_rows),
            procesadas=len(response_rows),
            observaciones=observations,
            resultados=response_rows,
        )
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fallo al procesar o guardar un CSV")
        raise HTTPException(status_code=500, detail="No se pudo procesar el CSV.") from exc

