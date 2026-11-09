from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.services.model_service import FEATURES, STUDENT_ID, TARGET, validate_feature_columns, validate_row


def parse_csv(raw: bytes) -> tuple[list[dict[str, Any]], list[str], str]:
    if not raw:
        raise ValueError("El archivo está vacío.")
    try:
        frame = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
    except UnicodeDecodeError:
        frame = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    except Exception as exc:
        raise ValueError("No se pudo leer el CSV. Verifica el delimitador y la codificación.") from exc
    if frame.empty:
        raise ValueError("El CSV no contiene registros.")
    if len(frame) > 5000:
        raise ValueError("El CSV supera el máximo de 5,000 filas por carga.")
    frame.columns = [str(column).strip() for column in frame.columns]
    unknown = validate_feature_columns(list(frame.columns))
    if unknown:
        raise ValueError("Columnas no reconocidas: " + ", ".join(unknown))
    observations: list[str] = []
    duplicates = frame[STUDENT_ID].astype(str).duplicated(keep="first")
    if duplicates.any():
        observations.append(f"Se detectaron {int(duplicates.sum())} códigos repetidos; se conservaron como filas independientes.")
    if TARGET in frame.columns:
        observations.append("Se encontró riesgo_academico: se conserva como estado real si es válido, pero nunca se usa como entrada del modelo.")
    rows: list[dict[str, Any]] = []
    for idx, raw_row in enumerate(frame.to_dict(orient="records"), start=2):
        student_id, features, actual = validate_row(raw_row, idx)
        source_features = features.model_dump()
        missing_fields = [name for name, value in source_features.items() if value is None or str(value).strip() == "" or pd.isna(value)]
        if missing_fields:
            observations.append(f"Fila {idx} ({student_id}): se imputarán {len(missing_fields)} campos faltantes con el pipeline entrenado.")
        rows.append({"estudiante_id": student_id, "features": features, "source_features": source_features, "estado_real": actual})
    return rows, observations, ",".join(frame.columns)

