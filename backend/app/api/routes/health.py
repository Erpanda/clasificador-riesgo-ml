from fastapi import APIRouter

from app.services.model_service import ModelNotReadyError, load_model, model_version

router = APIRouter(tags=["estado"])


@router.get("/health")
def health() -> dict[str, object]:
    try:
        load_model()
        return {"status": "ok", "model_ready": True, "model_version": model_version()}
    except ModelNotReadyError:
        return {"status": "ok", "model_ready": False, "detail": "Entrena el modelo antes de predecir."}

