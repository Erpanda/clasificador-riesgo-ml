from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier

from app.services.model_service import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, STUDENT_ID, TARGET
from app.services.database_service import save_evaluation


ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = ROOT / "backend" / "alternatives" / "our_model" / "artifacts"
LABELS = ["En riesgo", "Sin riesgo"]


def make_pipeline(classifier, scale_numeric: bool = False) -> Pipeline:
    numeric_steps = [("imputer", SimpleImputer(strategy="median", add_indicator=True))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent", add_indicator=True)),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])
    return Pipeline([("preprocessing", preprocessor), ("classifier", classifier)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena y evalúa los modelos candidatos.")
    parser.add_argument("csv", nargs="?", default=str(ROOT / "G1_Dataset_500_Riesgo_Academico.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data = pd.read_csv(args.csv, encoding="utf-8-sig")
    required = [STUDENT_ID, *FEATURES, TARGET]
    missing_columns = [name for name in required if name not in data.columns]
    if missing_columns:
        raise SystemExit("Faltan columnas: " + ", ".join(missing_columns))
    if data[TARGET].isna().any():
        raise SystemExit("Hay registros sin etiqueta riesgo_academico; sepáralos antes del entrenamiento.")
    if not set(data[TARGET].unique()).issubset(set(LABELS)):
        raise SystemExit("La etiqueta contiene valores distintos de En riesgo / Sin riesgo.")
    data = data.drop_duplicates()
    if data[STUDENT_ID].duplicated().any():
        raise SystemExit("Hay códigos de estudiante repetidos. Define primero cómo separar las observaciones del mismo estudiante para evitar fuga entre entrenamiento y prueba.")
    if data.empty:
        raise SystemExit("No quedan registros después de quitar duplicados exactos.")

    X = data[FEATURES].copy()
    y = data[TARGET].copy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=args.seed, stratify=y
    )

    candidates = {
        "Random Forest": make_pipeline(RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=args.seed, n_jobs=-1
        )),
        "Árbol de Decisión": make_pipeline(DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=5, class_weight="balanced", random_state=args.seed
        )),
        "KNN": make_pipeline(KNeighborsClassifier(n_neighbors=5, weights="distance"), scale_numeric=True),
    }
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)
    scores: dict[str, dict[str, float]] = {}
    for name, candidate in candidates.items():
        cv = cross_validate(
            candidate, X_train, y_train, cv=folds,
            scoring={
                "recall_riesgo": make_scorer(recall_score, pos_label="En riesgo", zero_division=0),
                "f1_riesgo": make_scorer(f1_score, pos_label="En riesgo", zero_division=0),
                "accuracy": "accuracy",
            },
            return_train_score=False,
        )
        scores[name] = {
            "recall_riesgo_cv_mean": float(cv["test_recall_riesgo"].mean()),
            "f1_riesgo_cv_mean": float(cv["test_f1_riesgo"].mean()),
            "accuracy_cv_mean": float(cv["test_accuracy"].mean()),
        }
    selected_name = max(scores, key=lambda name: (scores[name]["recall_riesgo_cv_mean"], scores[name]["f1_riesgo_cv_mean"]))
    selected = candidates[selected_name]
    selected.fit(X_train, y_train)
    predictions = selected.predict(X_test)
    risk_precision = precision_score(y_test, predictions, pos_label="En riesgo", zero_division=0)
    risk_recall = recall_score(y_test, predictions, pos_label="En riesgo", zero_division=0)
    risk_f1 = f1_score(y_test, predictions, pos_label="En riesgo", zero_division=0)
    matrix = confusion_matrix(y_test, predictions, labels=LABELS)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_en_riesgo": float(risk_precision),
        "recall_en_riesgo": float(risk_recall),
        "f1_en_riesgo": float(risk_f1),
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": matrix.tolist(),
        "classification_report": classification_report(y_test, predictions, labels=LABELS, target_names=LABELS, output_dict=True, zero_division=0),
        "cross_validation_candidates": scores,
        "selected_model": selected_name,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "random_seed": args.seed,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected, ARTIFACTS / "model.joblib")
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    reference_values: dict[str, object] = {
        name: float(X_train[name].median()) for name in NUMERIC_FEATURES
    }
    for name in CATEGORICAL_FEATURES:
        mode = X_train[name].mode(dropna=True)
        reference_values[name] = str(mode.iloc[0]) if not mode.empty else "No registrado"
    metadata = {
        "version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "selected_model": selected_name,
        "features": FEATURES,
        "target": TARGET,
        "reference_values": reference_values,
        "metrics_file": "metrics.json",
    }
    (ARTIFACTS / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    evaluation_saved = save_evaluation(metrics, metadata["version"], selected_name)
    reports = ROOT / "backend" / "alternatives" / "our_model" / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    # EDA: numeric distributions split by the known class, plus category counts.
    fig, axes = plt.subplots(4, 2, figsize=(12, 13))
    axes_flat = axes.flatten()
    class_colors = {"En riesgo": "#c6785b", "Sin riesgo": "#408b72"}
    for ax, feature in zip(axes_flat, NUMERIC_FEATURES, strict=False):
        # Draw green first so the orange risk distribution remains visible on top.
        for label in ["Sin riesgo", "En riesgo"]:
            values = pd.to_numeric(data.loc[y == label, feature], errors="coerce").dropna()
            ax.hist(values, bins=12, alpha=0.58, color=class_colors[label], label=label)
        ax.set_title(feature.replace("_", " ").capitalize(), loc="left", fontsize=10)
        ax.set_ylabel("Estudiantes")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    participation = pd.crosstab(data["participacion_aula"], y).reindex(columns=LABELS, fill_value=0)
    participation = participation.reindex(["Baja", "Media", "Alta"], fill_value=0)
    ax = axes_flat[len(NUMERIC_FEATURES)]
    participation.plot(kind="bar", ax=ax, color=[class_colors[label] for label in LABELS], width=0.72)
    ax.set_title("Participación en aula", loc="left", fontsize=10)
    ax.set_ylabel("Estudiantes"); ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=0)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    axes_flat[-1].axis("off")
    fig.suptitle("Distribución de valores por variable y clase", fontsize=15, y=1.01)
    fig.tight_layout(); fig.savefig(reports / "distribucion_variables.png", dpi=160, bbox_inches="tight"); plt.close(fig)

    class_counts = y.value_counts().reindex(LABELS, fill_value=0)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    bars = ax.bar(class_counts.index, class_counts.values, color=["#c6785b", "#408b72"], width=0.58)
    ax.bar_label(bars, padding=4, fontsize=10)
    ax.set_title("Distribución de clases del dataset")
    ax.set_ylabel("Cantidad de estudiantes")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(reports / "distribucion_clases.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.1, 4.8), constrained_layout=True)
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(2), LABELS); ax.set_yticks(range(2), LABELS)
    ax.set_xlabel("Predicción del modelo"); ax.set_ylabel("Estado real")
    ax.set_title("Matriz de confusión · prueba")
    for i in range(2):
        for j in range(2):
            color = "white" if matrix[i, j] > matrix.max() / 2 else "#183153"
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", color=color, fontsize=12)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Cantidad de estudiantes")
    fig.savefig(reports / "matriz_confusion.png", dpi=160); plt.close(fig)

    report_metrics = metrics["classification_report"]
    metric_names = ["precision", "recall", "f1-score"]
    x = list(range(len(LABELS)))
    width = 0.23
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for offset, metric, color in zip([-width, 0, width], metric_names, ["#55779a", "#c6785b", "#408b72"], strict=True):
        values = [report_metrics[label][metric] for label in LABELS]
        bars = ax.bar([position + offset for position in x], values, width, label=metric.capitalize(), color=color)
        ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    ax.set_xticks(x, LABELS); ax.set_ylim(0, 1.12)
    ax.set_ylabel("Puntaje en el conjunto de prueba")
    ax.set_title(f"Reporte de clasificación · {selected_name}")
    ax.legend(frameon=False, ncol=3)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout(); fig.savefig(reports / "reporte_clasificacion.png", dpi=160); plt.close(fig)

    candidate_names = list(scores)
    positions = list(range(len(candidate_names)))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for offset, metric, label, color in [
        (-width, "recall_riesgo_cv_mean", "Recall En riesgo", "#c6785b"),
        (0, "f1_riesgo_cv_mean", "F1 En riesgo", "#408b72"),
        (width, "accuracy_cv_mean", "Accuracy", "#55779a"),
    ]:
        bars = ax.bar([p + offset for p in positions], [scores[name][metric] for name in candidate_names], width, label=label, color=color)
        ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    ax.set_xticks(positions, candidate_names); ax.set_ylim(0, 1.12)
    ax.set_ylabel("Promedio de validación cruzada")
    ax.set_title("Comparación de modelos en entrenamiento")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(reports / "comparacion_modelos.png", dpi=160); plt.close(fig)

    try:
        classifier = selected.named_steps["classifier"]
        names = selected.named_steps["preprocessing"].get_feature_names_out()
        summary: dict[str, float] = {}
        for name, value in zip(names, classifier.feature_importances_, strict=True):
            readable = str(name).split("__", 1)[-1]
            summary[readable] = summary.get(readable, 0.0) + float(value)
        top = sorted(summary.items(), key=lambda pair: pair[1], reverse=True)[:8]
        top.reverse()
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.barh([item[0] for item in top], [item[1] for item in top], color="#408b72")
        ax.set_title(f"Variables relevantes · {selected_name}")
        ax.set_xlabel("Importancia interna del modelo")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); fig.savefig(reports / "importancia_variables.png", dpi=160); plt.close(fig)
    except (AttributeError, ValueError):
        pass
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"Evaluación guardada en Supabase: {'sí' if evaluation_saved else 'no (faltan credenciales)'}")
    print(f"Modelo guardado en {ARTIFACTS / 'model.joblib'}")


if __name__ == "__main__":
    main()

