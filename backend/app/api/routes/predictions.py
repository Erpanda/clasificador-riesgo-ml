from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.prediction import PredictionResult
from app.schemas.student import ManualPredictionRequest, StudentFeatures
from app.services.database_service import save_manual
from app.services.model_service import ModelNotReadyError, model_version, predict_one


router = APIRouter(prefix="/predictions", tags=["predicciones"])
logger = logging.getLogger(__name__)


@router.post("/manual", response_model=PredictionResult)
def predict_manual(request: ManualPredictionRequest) -> PredictionResult:
    try:
        features = StudentFeatures(**request.model_dump(exclude={"estudiante_id"}))
        label, probability, factors = predict_one(features)
        saved = save_manual(
            request.estudiante_id,
            features,
            None,
            {
                "estado_predicho": label,
                "probabilidad_riesgo": probability,
                "version_modelo": model_version(),
                "factores": [item.model_dump() for item in factors],
            },
        )
        return PredictionResult(
            estudiante_id=request.estudiante_id,
            datos_entrada=features.model_dump(),
            estado_predicho=label,
            probabilidad_riesgo=round(probability, 4),
            factores=factors,
            version_modelo=model_version(),
            guardado=saved,
        )
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fallo al generar o guardar una predicción manual")
        raise HTTPException(status_code=500, detail="No se pudo completar la predicción.") from exc

