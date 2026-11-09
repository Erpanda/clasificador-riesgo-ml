from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.inspection import permutation_importance

from app.core.config import MODEL_METADATA_PATH, MODEL_PATH
from scripts.generate_model_report import generate_report
from app.services.database_service import save_evaluation
from app.services.model_service import FEATURES, PARTICIPATION_TO_CODE


ROOT = Path(__file__).resolve().parents[2]
X_PATH = ROOT / "backend" / "data" / "X_predictoras.csv"
Y_PATH = ROOT / "backend" / "data" / "y_objetivo.csv"
REPORTS = ROOT / "backend" / "reports"
LABELS = [0, 1]  # 0 = Sin riesgo, 1 = En riesgo


def print_training_report(metrics: dict, metadata: dict, reports_dir: Path, evaluation_saved: bool) -> None:
    def section(title: str) -> None:
        print(f"\n{title}")
        print("-" * max(30, len(title)))

    print("REPORTE DE ENTRENAMIENTO Y EVALUACIÓN")
    print("=" * 60)
    print(f"Modelo activo: {metadata['selected_model']}")
    print(f"Registros de entrenamiento: {metadata['training_rows']}")
    print(f"Registros de prueba: {metadata['test_rows']}")
    print(f"Semilla aleatoria: {metadata['random_seed']}")

    section("1. COMPARACIÓN DE MODELOS")
    comparison = pd.DataFrame([
        {"Modelo": name, "Exactitud": f"{score:.1%}", "Seleccionado": "Sí" if name == metadata["selected_model"] else "No"}
        for name, score in metrics["model_comparison_accuracy"].items()
    ])
    print(comparison.to_string(index=False))
    print("Criterio: se seleccionó el modelo con mayor exactitud en el conjunto de prueba.")

    section("2. MÉTRICAS POR CLASE")
    report = metrics["classification_report"]
    class_rows = [
        {
            "Clase": label,
            "Precisión": f"{report[label]['precision']:.3f}",
            "Recall": f"{report[label]['recall']:.3f}",
            "F1-score": f"{report[label]['f1-score']:.3f}",
            "Registros": int(report[label]["support"]),
        }
        for label in ("Sin riesgo", "En riesgo")
    ]
    class_table = pd.DataFrame(class_rows)
    accuracy = metrics["accuracy"]
    class_table.loc[len(class_table)] = {
        "Clase": "accuracy", "Precisión": f"{accuracy:.3f}",
        "Recall": f"{accuracy:.3f}", "F1-score": f"{accuracy:.3f}",
        "Registros": f"{accuracy:.3f}",
    }
    for average in ("macro avg", "weighted avg"):
        row = report[average]
        class_table.loc[len(class_table)] = {
            "Clase": average,
            "Precisión": f"{row['precision']:.3f}",
            "Recall": f"{row['recall']:.3f}",
            "F1-score": f"{row['f1-score']:.3f}",
            "Registros": int(row["support"]),
        }
    print(class_table.to_string(index=False))

    section("3. MATRIZ DE CONFUSIÓN")
    matrix_table = pd.DataFrame(
        metrics["confusion_matrix"],
        index=["Real: Sin riesgo", "Real: En riesgo"],
        columns=["Predicho: Sin riesgo", "Predicho: En riesgo"],
    )
    print(matrix_table.to_string())

    section("4. ARCHIVOS GENERADOS")
    print(f"Modelo: {MODEL_PATH}")
    print(f"Metadatos y métricas: {MODEL_METADATA_PATH.parent}")
    print(f"Imágenes y reporte Markdown: {reports_dir}")
    print(f"Evaluación guardada en Supabase: {'Sí' if evaluation_saved else 'No (faltan credenciales)'}")


def main():
    if not X_PATH.exists() or not Y_PATH.exists():
        raise SystemExit(f"No se encontraron los archivos: {X_PATH} y {Y_PATH}.")

    X = pd.read_csv(X_PATH, encoding="utf-8-sig")
    y_frame = pd.read_csv(Y_PATH, encoding="utf-8-sig")
    if list(X.columns) != FEATURES:
        raise SystemExit(f"Las columnas de X deben ser exactamente: {', '.join(FEATURES)}.")
    if y_frame.shape[1] != 1 or len(X) != len(y_frame):
        raise SystemExit("X e y deben tener la misma cantidad de filas y y debe tener una sola columna.")

    X = X.copy()
    X["participacion_aula"] = X["participacion_aula"].replace(
        {label: code for label, code in PARTICIPATION_TO_CODE.items()}
    )
    X["participacion_aula"] = pd.to_numeric(X["participacion_aula"], errors="raise").astype(int)
    y = pd.to_numeric(y_frame.iloc[:, 0], errors="raise").astype(int)
    if set(y.unique()) != {0, 1}:
        raise SystemExit("La columna objetivo debe usar 0 = Sin riesgo y 1 = En riesgo.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    # Reproduce los tres algoritmos y el criterio de selección.
    models = {
        "Árbol de Decisión": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(random_state=42),
        "KNN": Pipeline([
            ("escalador", StandardScaler()),
            ("knn", KNeighborsClassifier(n_neighbors=5)),
        ]),
    }
    candidate_metrics: dict[str, float] = {}
    candidate_predictions: dict[str, pd.Series] = {}
    for name, candidate in models.items():
        candidate.fit(X_train, y_train)
        candidate_predictions[name] = candidate.predict(X_test)
        candidate_metrics[name] = float(accuracy_score(y_test, candidate_predictions[name]))

    selected_name = max(candidate_metrics, key=candidate_metrics.get)
    model = models[selected_name]
    predictions = candidate_predictions[selected_name]
    matrix = confusion_matrix(y_test, predictions, labels=LABELS)
    labels = ["Sin riesgo", "En riesgo"]
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_en_riesgo": float(precision_score(y_test, predictions, pos_label=1, zero_division=0)),
        "recall_en_riesgo": float(recall_score(y_test, predictions, pos_label=1, zero_division=0)),
        "f1_en_riesgo": float(f1_score(y_test, predictions, pos_label=1, zero_division=0)),
        "confusion_matrix_labels": labels,
        "confusion_matrix": matrix.tolist(),
        "classification_report": classification_report(
            y_test, predictions, labels=LABELS, target_names=labels,
            output_dict=True, zero_division=0,
        ),
        "selected_model": selected_name,
        "model_comparison_accuracy": candidate_metrics,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "random_seed": 42,
        "source_X": str(X_PATH.relative_to(ROOT)),
        "source_y": str(Y_PATH.relative_to(ROOT)),
    }

    references: dict[str, float | int] = {}
    for feature in FEATURES:
        if feature == "participacion_aula":
            references[feature] = int(X_train[feature].mode().iloc[0])
        else:
            references[feature] = float(X_train[feature].median())

    metadata = {
        "version": "clasificador-riesgo-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "selected_model": selected_name,
        "model_comparison_accuracy": candidate_metrics,
        "features": FEATURES,
        "target": "riesgo_academico",
        "label_mapping": {"0": "Sin riesgo", "1": "En riesgo"},
        "participation_mapping": PARTICIPATION_TO_CODE,
        "reference_values": references,
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "random_seed": 42,
        "source_X": str(X_PATH.relative_to(ROOT)),
        "source_y": str(Y_PATH.relative_to(ROOT)),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    MODEL_METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path = MODEL_METADATA_PATH.with_name("metrics.json")
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    generate_report(
        metrics_path=metrics_path,
        metadata_path=MODEL_METADATA_PATH,
        output_path=REPORTS / "reporte_modelo.md",
    )
    evaluation_saved = save_evaluation(metrics, metadata["version"], selected_name)

    # Distribución de las variables predictoras según la etiqueta conocida.
    colors = {0: "#408b72", 1: "#c6785b"}
    feature_names = [
        "asistencia_pct", "promedio_parcial", "horas_estudio",
        "tareas_entregadas_pct", "participacion_aula",
        "cursos_desaprobados", "actividad_plataforma",
    ]
    fig, axes = plt.subplots(4, 2, figsize=(12, 13))
    axes_flat = axes.flatten()
    for ax, feature in zip(axes_flat, feature_names, strict=False):
        if feature == "participacion_aula":
            categories = [0, 1, 2]
            counts = pd.crosstab(X[feature], y).reindex(index=categories, columns=LABELS, fill_value=0)
            width = 0.36
            positions = list(range(len(categories)))
            for offset, label in zip([-width / 2, width / 2], LABELS, strict=True):
                bars = ax.bar([p + offset for p in positions], counts[label], width,
                              color=colors[label], label=labels[LABELS.index(label)])
            ax.set_xticks(positions, ["Baja", "Media", "Alta"])
            ax.set_ylabel("Estudiantes")
        else:
            # Dibujar primero la clase verde para que la naranja quede encima y visible.
            for label in LABELS:
                ax.hist(X.loc[y == label, feature], bins=12, alpha=0.58,
                        color=colors[label], label=labels[LABELS.index(label)])
            ax.set_ylabel("Estudiantes")
        ax.set_title(feature.replace("_", " ").capitalize(), loc="left", fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    axes_flat[-1].axis("off")
    fig.suptitle("Distribución de valores por variable y clase", fontsize=15, y=1.01)
    fig.tight_layout()
    fig.savefig(REPORTS / "imgs" / "distribucion_variables.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    comparison_names = list(candidate_metrics)
    comparison_values = [candidate_metrics[name] * 100 for name in comparison_names]
    bars = ax.bar(comparison_names, comparison_values, color=["#408b72", "#55779a", "#c6785b"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Exactitud (%)")
    ax.set_title("Comparación de exactitud de los modelos")
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "imgs" / "comparacion_modelos.png", dpi=160)
    plt.close(fig)

    # Matriz de confusión: las filas son el estado real y las columnas la predicción.
    fig, ax = plt.subplots(figsize=(6.2, 4.9), constrained_layout=True)
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(2), labels)
    ax.set_yticks(range(2), labels)
    ax.set_xlabel("Predicción del modelo")
    ax.set_ylabel("Estado real")
    ax.set_title("Matriz de confusión · prueba")
    for row in range(2):
        for column in range(2):
            color = "white" if matrix[row, column] > matrix.max() / 2 else "#183153"
            ax.text(column, row, str(matrix[row, column]), ha="center", va="center",
                    color=color, fontsize=12)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Cantidad de estudiantes")
    fig.savefig(REPORTS / "imgs" / "matriz_confusion.png", dpi=160)
    plt.close(fig)

    # Precision, recall y F1 por clase en el conjunto de prueba.
    report = metrics["classification_report"]
    metric_names = [("precision", "Precisión", "#55779a"),
                    ("recall", "Recall", "#c6785b"), ("f1-score", "F1", "#408b72")]
    positions = list(range(len(labels)))
    width = 0.23
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for offset, (key, title, color) in zip([-width, 0, width], metric_names, strict=True):
        values = [report[label][key] for label in labels]
        bars = ax.bar([position + offset for position in positions], values,
                      width, label=title, color=color)
        ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Puntaje en el conjunto de prueba")
    ax.set_title(f"Reporte de clasificación · {selected_name}")
    ax.legend(frameon=False, ncol=3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "imgs" / "reporte_clasificacion.png", dpi=160)
    plt.close(fig)

    # Importancia por permutación, compatible con los tres algoritmos.
    permutation = permutation_importance(
        model, X_test, y_test, n_repeats=10, random_state=42, scoring="accuracy"
    )
    importances = pd.Series(permutation.importances_mean, index=feature_names).sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(importances.index, importances.values, color="#408b72")
    ax.set_title(f"Importancia de variables · {selected_name}")
    ax.set_xlabel("Disminución media de exactitud al permutar")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORTS / "imgs" / "importancia_variables.png", dpi=160)
    plt.close(fig)

    print_training_report(metrics, metadata, REPORTS, evaluation_saved)


if __name__ == "__main__":
    main()
