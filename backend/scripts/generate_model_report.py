from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "backend" / "app" / "artifacts" / "project_model"
DEFAULT_METRICS = ARTIFACTS / "metrics.json"
DEFAULT_METADATA = ARTIFACTS / "model_metadata.json"
DEFAULT_OUTPUT = ROOT / "backend" / "reports" / "reporte_modelo.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo requerido: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report(
    metrics_path: Path = DEFAULT_METRICS,
    metadata_path: Path = DEFAULT_METADATA,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    metrics = _read_json(metrics_path)
    metadata = _read_json(metadata_path)
    classification = metrics["classification_report"]
    comparison = metrics["model_comparison_accuracy"]
    selected = metrics["selected_model"]
    selected_accuracy = comparison[selected]

    class_rows = []
    for label in ("Sin riesgo", "En riesgo"):
        row = classification[label]
        class_rows.append(
            f"| {label} | {row['precision']:.3f} | {row['recall']:.3f} | "
            f"{row['f1-score']:.3f} | {row['support']:.0f} |"
        )

    accuracy = classification["accuracy"]
    class_rows.append(
        f"| accuracy | {accuracy:.3f} | {accuracy:.3f} | {accuracy:.3f} | {accuracy:.3f} |"
    )
    for key, label in (("macro avg", "macro avg"), ("weighted avg", "weighted avg")):
        row = classification[key]
        class_rows.append(
            f"| {label} | {row['precision']:.3f} | {row['recall']:.3f} | "
            f"{row['f1-score']:.3f} | {row['support']:.0f} |"
        )

    comparison_rows = [
        f"| {name} | {score:.1%} |" for name, score in comparison.items()
    ]
    model_reason = (
        f"Se seleccionó **{selected}** porque alcanzó la mayor exactitud "
        f"({selected_accuracy:.1%}) entre los tres candidatos en el conjunto de prueba. "
        "Este criterio reproduce el utilizado en `Entrenamiento.py`."
    )
    risk = classification["En riesgo"]
    report = f"""# Reporte de selección y clasificación del modelo

## Datos y procedimiento

- Datos de entrada: `{metadata['source_X']}` y `{metadata['source_y']}`.
- División estratificada: 80 % entrenamiento ({metadata['training_rows']} registros) y 20 % prueba ({metadata['test_rows']} registros).
- Semilla aleatoria: {metadata['random_seed']}.
- Modelos comparados: Árbol de Decisión, Random Forest y KNN con escalado estándar.
- Etiquetas: `0 = Sin riesgo`, `1 = En riesgo`.

## Comparación de modelos

| Modelo | Exactitud en prueba |
|---|---:|
{chr(10).join(comparison_rows)}

## Modelo seleccionado

{model_reason}

La exactitud indica la proporción total de predicciones correctas. La tabla siguiente agrega precisión, recall y F1 por clase, en particular para la detección de estudiantes **En riesgo**.

## Reporte de clasificación: {selected}

| Clase | Precisión | Recall | F1-score | Registros |
|---|---:|---:|---:|---:|
{chr(10).join(class_rows)}

## Lectura de la clase “En riesgo”

- **Precisión ({risk['precision']:.3f}):** proporción de las predicciones “En riesgo” que correspondió a estudiantes realmente en esa clase.
- **Recall ({risk['recall']:.3f}):** proporción de estudiantes realmente “En riesgo” que el modelo detectó.
- **F1-score ({risk['f1-score']:.3f}):** combina precisión y recall en una sola medida.

Las métricas describen el desempeño observado en esta partición de prueba; no garantizan el mismo resultado en otros grupos.
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el reporte Markdown del modelo entrenado.")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = generate_report(args.metrics, args.metadata, args.output)
    print(f"Reporte Markdown generado: {output_path}")


if __name__ == "__main__":
    main()
