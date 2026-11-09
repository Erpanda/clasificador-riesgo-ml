from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.services.model_service import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, STUDENT_ID, TARGET

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DATA_DIR = ROOT / "backend" / "data"
PARTICIPATION_CODES = {"Baja": 0, "Media": 1, "Alta": 2}
TARGET_CODES = {"Sin riesgo": 0, "En riesgo": 1}

def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * max(30, len(title)))

def print_table(frame: pd.DataFrame, *, index: bool = False) -> None:
    if frame.empty:
        print("(sin datos)")
    else:
        print(frame.to_string(index=index))

def main():
    parser = argparse.ArgumentParser(description="Audita el CSV del proyecto sin modificarlo.")
    parser.add_argument("csv", nargs="?", default=BACKEND_DATA_DIR / "G1_Dataset_500_Riesgo_Academico.csv")
    parser.add_argument("--output-dir", type=Path, default=BACKEND_DATA_DIR,
                        help="Carpeta donde guardar X_predictoras.csv y y_objetivo.csv.")
    args = parser.parse_args()
    path = Path(args.csv)
    if not path.exists():
        raise SystemExit(f"No se encontró el archivo: {path}")

    try:
        frame = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:
        raise SystemExit(f"No se pudo leer el CSV: {exc}") from exc

    required = [STUDENT_ID, *FEATURES, TARGET]
    missing_columns = [column for column in required if column not in frame.columns]
    missing_cells = frame.isna().sum()
    missing_total = int(missing_cells.sum())
    duplicate_ids = int(frame[STUDENT_ID].duplicated().sum()) if STUDENT_ID in frame else None
    duplicate_rows = int(frame.duplicated().sum())
    invalid_labels = None
    invalid_participation = None
    range_violations: dict[str, int] = {}

    print("REPORTE DE AUDITORÍA DEL DATASET")
    print("=" * 60)
    print(f"Archivo revisado: {path}")
    print(f"Registros: {len(frame)}")
    print(f"Columnas: {len(frame.columns)}")
    print("Columnas detectadas: " + ", ".join(map(str, frame.columns)))

    section("1. ESTRUCTURA Y COLUMNAS REQUERIDAS")
    print(f"Columnas obligatorias: {len(required)}")
    print("Columnas faltantes: " + (", ".join(missing_columns) if missing_columns else "ninguna"))

    section("2. VALORES FALTANTES")
    missing_table = pd.DataFrame({"Columna": missing_cells.index, "Valores faltantes": missing_cells.values})
    print_table(missing_table)
    print(f"Total de celdas faltantes: {missing_total}")

    section("3. DUPLICADOS")
    print(f"Códigos de estudiante repetidos: {duplicate_ids if duplicate_ids is not None else 'no evaluable (falta la columna)'}")
    print(f"Filas duplicadas exactas: {duplicate_rows}")

    if TARGET in frame.columns:
        section("4. DISTRIBUCIÓN DE LA ETIQUETA")
        counts = frame[TARGET].value_counts(dropna=False)
        class_table = pd.DataFrame({
            "Estado": counts.index.astype(str),
            "Registros": counts.values,
            "Porcentaje": (counts.values / len(frame) * 100).round(2) if len(frame) else [],
        })
        print_table(class_table)
        invalid_labels = int((frame[TARGET].notna() & ~frame[TARGET].isin(TARGET_CODES)).sum())
        print(f"Etiquetas inválidas: {invalid_labels}")

    categorical_columns = [column for column in CATEGORICAL_FEATURES if column in frame.columns]
    if categorical_columns:
        section("5. DISTRIBUCIÓN DE VARIABLES CATEGÓRICAS")
        for column in categorical_columns:
            print(f"\n{column}:")
            counts = frame[column].value_counts(dropna=False)
            table = pd.DataFrame({"Valor": counts.index.astype(str), "Registros": counts.values})
            print_table(table)
        invalid_participation = int((frame["participacion_aula"].notna() & ~frame["participacion_aula"].isin(PARTICIPATION_CODES)).sum())
        print(f"Categorías de participación inválidas: {invalid_participation}")

    numeric_columns = [column for column in NUMERIC_FEATURES if column in frame.columns]
    if numeric_columns:
        section("6. RESUMEN DE VARIABLES NUMÉRICAS")
        summary = frame[numeric_columns].describe().T
        summary = summary.rename(columns={"count": "Registros", "mean": "Media", "std": "Desv. estándar", "min": "Mínimo", "max": "Máximo"})
        summary = summary[["Registros", "Media", "Desv. estándar", "Mínimo", "Máximo", "50%"]]
        summary = summary.rename(columns={"max": "Máximo", "50%": "Mediana"}).round(2)
        summary.insert(0, "Variable", summary.index)
        print_table(summary.reset_index(drop=True))

    ranges = {
        "asistencia_pct": (0, 100),
        "promedio_parcial": (0, 20),
        "tareas_entregadas_pct": (0, 100),
    }
    if any(column in frame.columns for column in ranges):
        section("7. VALIDACIÓN DE RANGOS")
        range_rows = []
        for column, (lower, upper) in ranges.items():
            if column not in frame.columns:
                range_rows.append({"Variable": column, "Rango esperado": f"{lower}–{upper}", "Fuera de rango": "no evaluable"})
                continue
            values = pd.to_numeric(frame[column], errors="coerce")
            invalid = int((values.notna() & ~values.between(lower, upper)).sum())
            range_violations[column] = invalid
            range_rows.append({"Variable": column, "Rango esperado": f"{lower}–{upper}", "Fuera de rango": invalid})
        print_table(pd.DataFrame(range_rows))

    section("8. PREPARACIÓN DE X E Y PARA ENTRENAMIENTO")
    export_blockers = []
    if missing_columns:
        export_blockers.append("faltan columnas requeridas")
    if missing_total:
        export_blockers.append("hay valores vacíos")
    if duplicate_ids:
        export_blockers.append("hay códigos de estudiante repetidos")
    if duplicate_rows:
        export_blockers.append("hay filas duplicadas exactas")
    if invalid_labels:
        export_blockers.append("hay etiquetas objetivo no reconocidas")
    if invalid_participation:
        export_blockers.append("hay categorías de participación no reconocidas")
    if any(range_violations.values()):
        export_blockers.append("hay valores fuera de rango")

    if export_blockers:
        print("No se generaron los archivos X/y: " + "; ".join(export_blockers) + ".")
    else:
        X = frame[FEATURES].copy()
        for column in NUMERIC_FEATURES:
            X[column] = pd.to_numeric(X[column], errors="raise")

        X["participacion_aula"] = X["participacion_aula"].map(PARTICIPATION_CODES).astype(int)
        y = pd.DataFrame({TARGET: frame[TARGET].map(TARGET_CODES).astype(int)})
        args.output_dir.mkdir(parents=True, exist_ok=True)

        x_path = args.output_dir / "X_predictoras.csv"
        y_path = args.output_dir / "y_objetivo.csv"

        X.to_csv(x_path, index=False, encoding="utf-8-sig")
        y.to_csv(y_path, index=False, encoding="utf-8-sig")

        print("Se generaron los archivos preparados, conservando los 500 registros y su orden:")
        print(f"- X (variables predictoras; sin código de estudiante ni objetivo): {x_path}")
        print(f"- y (objetivo codificado: 0 = Sin riesgo, 1 = En riesgo): {y_path}")
        print("Codificación de participación: Baja = 0, Media = 1, Alta = 2.")

    section("RESUMEN")
    if missing_columns:
        print("Resultado: incompleto. Faltan columnas obligatorias; revisa la estructura antes de usar el archivo.")
        raise SystemExit(1)
    if missing_total or duplicate_ids or duplicate_rows:
        print("Resultado: revisar. Se encontraron valores faltantes o registros/códigos duplicados.")
    else:
        print("Resultado: estructura completa, sin faltantes ni duplicados detectados.")
    print("La auditoría es informativa: no modifica ni limpia el CSV.")


if __name__ == "__main__":
    main()
