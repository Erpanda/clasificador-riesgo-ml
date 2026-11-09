from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any

import joblib
import pandas as pd

from app.core.config import MODEL_METADATA_PATH, MODEL_PATH
from app.schemas.prediction import FactorDetail
from app.schemas.student import StudentFeatures

FEATURES = [
    "asistencia_pct", "promedio_parcial", "horas_estudio", "tareas_entregadas_pct",
    "participacion_aula", "cursos_desaprobados", "actividad_plataforma",
]
NUMERIC_FEATURES = [
    "asistencia_pct", "promedio_parcial", "horas_estudio", "tareas_entregadas_pct",
    "cursos_desaprobados", "actividad_plataforma",
]
CATEGORICAL_FEATURES = ["participacion_aula"]
TARGET = "riesgo_academico"
STUDENT_ID = "estudiante_id"
VALID_LABELS = {"En riesgo", "Sin riesgo"}
PARTICIPATION_TO_CODE = {"Baja": 0, "Media": 1, "Alta": 2}
CODE_TO_PARTICIPATION = {value: key for key, value in PARTICIPATION_TO_CODE.items()}
CODE_TO_LABEL = {0: "Sin riesgo", 1: "En riesgo"}


class ModelNotReadyError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_model() -> Any:
    if not MODEL_PATH.exists():
        raise ModelNotReadyError("El modelo todavía no está entrenado. Ejecuta backend/scripts/train_model.py.")
    model = joblib.load(MODEL_PATH)
    model_features = list(getattr(model, "feature_names_in_", []))
    if model_features and model_features != FEATURES:
        raise ModelNotReadyError("El orden de variables del modelo guardado no coincide con el esquema de la API.")
    return model


@lru_cache(maxsize=1)
def load_metadata() -> dict[str, Any]:
    if not MODEL_METADATA_PATH.exists():
        return {"version": "sin-version", "features": FEATURES}
    return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))


def predict_one(features: StudentFeatures) -> tuple[str, float, list[FactorDetail]]:
    model = load_model()
    values = features.model_dump()
    baseline = load_metadata().get("reference_values", {})
    prepared = {name: values[name] for name in FEATURES}
    for name in FEATURES:
        if prepared[name] is None:
            if name not in baseline:
                raise ValueError(f"No hay referencia de entrenamiento para completar {name}.")
            prepared[name] = baseline[name]
    prepared["participacion_aula"] = PARTICIPATION_TO_CODE[str(prepared["participacion_aula"])]
    frame = pd.DataFrame([{name: prepared[name] for name in FEATURES}], columns=FEATURES)
    predicted_code = int(model.predict(frame)[0])
    predicted = CODE_TO_LABEL[predicted_code]
    risk_index = [int(label) for label in model.classes_].index(1)
    risk_probability = float(model.predict_proba(frame)[0][risk_index])
    factors: list[FactorDetail] = []
    for feature in FEATURES:
        reference = baseline.get(feature)
        if reference is None or reference == prepared[feature]:
            continue
        altered = dict(prepared)
        altered[feature] = reference
        if feature == "participacion_aula":
            altered[feature] = int(reference)
        changed_frame = pd.DataFrame([{name: altered[name] for name in FEATURES}], columns=FEATURES)
        changed_probability = float(model.predict_proba(changed_frame)[0][risk_index])
        delta = risk_probability - changed_probability
        interpretation = (
            "La probabilidad estimada sube frente al valor de referencia." if delta > 0.005 else
            "La probabilidad estimada baja frente al valor de referencia." if delta < -0.005 else
            "El cambio frente al valor de referencia es pequeño."
        )
        factors.append(FactorDetail(
            variable=feature, valor=values[feature],
            cambio_estimado_probabilidad=round(delta, 4), interpretacion=interpretation,
        ))
    factors.sort(key=lambda item: abs(item.cambio_estimado_probabilidad), reverse=True)
    return predicted, risk_probability, factors[:4]


def model_version() -> str:
    return str(load_metadata().get("version", "sin-version"))


def validate_feature_columns(columns: list[str]) -> list[str]:
    missing = [name for name in [STUDENT_ID, *FEATURES] if name not in columns]
    if missing:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(missing))
    accepted = {STUDENT_ID, TARGET, "estado_real", "riesgo_predicho", *FEATURES}
    return [name for name in columns if name not in accepted]


def validate_row(row: dict[str, Any], row_number: int) -> tuple[str, StudentFeatures, str | None]:
    student_id = str(row.get(STUDENT_ID, "")).strip()
    if not student_id:
        raise ValueError(f"Fila {row_number}: falta {STUDENT_ID}.")
    payload: dict[str, Any] = {}
    for name in FEATURES:
        value = row.get(name)
        if value is None or bool(pd.isna(value)) or str(value).strip() == "":
            payload[name] = None
        else:
            payload[name] = value
    raw_actual = row.get(TARGET, row.get("estado_real"))
    actual = str(raw_actual).strip() if raw_actual is not None and not bool(pd.isna(raw_actual)) and str(raw_actual).strip() else None
    if actual is not None and actual not in VALID_LABELS:
        raise ValueError(f"Fila {row_number}: etiqueta real inválida: {actual}.")
    for field in NUMERIC_FEATURES:
        if payload[field] is not None:
            try:
                payload[field] = float(payload[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Fila {row_number}: {field} no es numérico.") from exc
            if not math.isfinite(payload[field]):
                raise ValueError(f"Fila {row_number}: {field} debe ser un número finito.")
    for field in ("cursos_desaprobados", "actividad_plataforma"):
        if payload[field] is not None and not float(payload[field]).is_integer():
            raise ValueError(f"Fila {row_number}: {field} debe ser entero.")
        if payload[field] is not None:
            payload[field] = int(payload[field])
    for field, lower, upper in (("asistencia_pct", 0, 100), ("promedio_parcial", 0, 20), ("tareas_entregadas_pct", 0, 100)):
        value = payload[field]
        if value is not None and not lower <= value <= upper:
            raise ValueError(f"Fila {row_number}: {field} debe estar entre {lower} y {upper}.")
    for field in ("horas_estudio", "cursos_desaprobados", "actividad_plataforma"):
        if payload[field] is not None and payload[field] < 0:
            raise ValueError(f"Fila {row_number}: {field} no puede ser negativo.")
    participation = payload["participacion_aula"]
    if participation is not None and participation not in {"Baja", "Media", "Alta"}:
        try:
            numeric_code = int(participation)
        except (TypeError, ValueError):
            numeric_code = -1
        if numeric_code not in CODE_TO_PARTICIPATION or str(numeric_code) != str(participation).strip():
            raise ValueError(f"Fila {row_number}: participacion_aula debe ser Baja, Media, Alta o su código 0, 1, 2.")
        payload["participacion_aula"] = CODE_TO_PARTICIPATION[numeric_code]
    return student_id, StudentFeatures.model_construct(**payload), actual
