from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from app.core.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.schemas.student import StudentFeatures


def get_client() -> Client | None:
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def save_manual(student_id: str, features: StudentFeatures, actual: str | None, prediction: dict[str, Any]) -> bool:
    client = get_client()
    if client is None:
        return False
    record = insert_record(client, student_id, features.model_dump(), actual, None)
    insert_prediction(client, record["id"], prediction)
    return True


def save_batch(file_name: str, rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> str | None:
    client = get_client()
    if client is None:
        return None
    batch = client.table("cargas_csv").insert({"nombre_archivo": file_name, "cantidad_filas": len(rows)}).execute().data[0]
    record_payloads = [
        {
            "estudiante_id": row["estudiante_id"],
            **row["features"],
            "estado_real": row["estado_real"],
            "carga_id": batch["id"],
        }
        for row in rows
    ]
    records = _insert_in_chunks(client, "registros_academicos", record_payloads)
    classification_payloads = [
        {
            "registro_id": record["id"],
            "estado_predicho": prediction["estado_predicho"],
            "probabilidad_riesgo": prediction["probabilidad_riesgo"],
            "version_modelo": prediction["version_modelo"],
        }
        for record, prediction in zip(records, predictions, strict=True)
    ]
    classifications = _insert_in_chunks(client, "clasificaciones", classification_payloads)
    detail_payloads = [
        {
            "clasificacion_id": classification["id"],
            "variable": item["variable"],
            "valor": str(item["valor"]),
            "cambio_estimado_probabilidad": item["cambio_estimado_probabilidad"],
            "interpretacion": item["interpretacion"],
        }
        for classification, prediction in zip(classifications, predictions, strict=True)
        for item in prediction.get("factores", [])
    ]
    if detail_payloads:
        _insert_in_chunks(client, "detalles_clasificacion", detail_payloads)
    return str(batch["id"])


def _insert_in_chunks(client: Client, table: str, rows: list[dict[str, Any]], size: int = 500) -> list[dict[str, Any]]:
    inserted: list[dict[str, Any]] = []
    for start in range(0, len(rows), size):
        inserted.extend(client.table(table).insert(rows[start:start + size]).execute().data)
    return inserted


def insert_record(client: Client, student_id: str, features: dict[str, Any], actual: str | None, batch_id: str | None) -> dict[str, Any]:
    payload = {
        "estudiante_id": student_id,
        **features,
        "estado_real": actual,
        "carga_id": batch_id,
    }
    return client.table("registros_academicos").insert(payload).execute().data[0]


def insert_prediction(client: Client, record_id: str, prediction: dict[str, Any]) -> dict[str, Any]:
    result = client.table("clasificaciones").insert({
        "registro_id": record_id,
        "estado_predicho": prediction["estado_predicho"],
        "probabilidad_riesgo": prediction["probabilidad_riesgo"],
        "version_modelo": prediction["version_modelo"],
    }).execute().data[0]
    details = prediction.get("factores", [])
    if details:
        client.table("detalles_clasificacion").insert([
            {
                "clasificacion_id": result["id"],
                "variable": item["variable"],
                "valor": str(item["valor"]),
                "cambio_estimado_probabilidad": item["cambio_estimado_probabilidad"],
                "interpretacion": item["interpretacion"],
            }
            for item in details
        ]).execute()
    return result


def save_evaluation(metrics: dict[str, Any], version: str, algorithm: str) -> bool:
    client = get_client()
    if client is None:
        return False
    client.table("evaluaciones_modelo").insert({
        "version_modelo": version,
        "algoritmo": algorithm,
        "accuracy": metrics["accuracy"],
        "precision_en_riesgo": metrics["precision_en_riesgo"],
        "recall_en_riesgo": metrics["recall_en_riesgo"],
        "f1_en_riesgo": metrics["f1_en_riesgo"],
        "matriz_confusion": {
            "labels": metrics["confusion_matrix_labels"],
            "values": metrics["confusion_matrix"],
        },
    }).execute()
    return True

