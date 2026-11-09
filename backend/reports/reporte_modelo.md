# Reporte de selección y clasificación del modelo

## Datos y procedimiento

- Datos de entrada: `backend\data\X_predictoras.csv` y `backend\data\y_objetivo.csv`.
- División estratificada: 80 % entrenamiento (400 registros) y 20 % prueba (100 registros).
- Semilla aleatoria: 42.
- Modelos comparados: Árbol de Decisión, Random Forest y KNN con escalado estándar.
- Etiquetas: `0 = Sin riesgo`, `1 = En riesgo`.

## Comparación de modelos

| Modelo | Exactitud en prueba |
|---|---:|
| Árbol de Decisión | 67.0% |
| Random Forest | 64.0% |
| KNN | 59.0% |

## Modelo seleccionado

Se seleccionó **Árbol de Decisión** porque alcanzó la mayor exactitud (67.0%) entre los tres candidatos en el conjunto de prueba. Este criterio reproduce el utilizado en `Entrenamiento.py`.

La exactitud indica la proporción total de predicciones correctas. La tabla siguiente agrega precisión, recall y F1 por clase, en particular para la detección de estudiantes **En riesgo**.

## Reporte de clasificación: Árbol de Decisión

| Clase | Precisión | Recall | F1-score | Registros |
|---|---:|---:|---:|---:|
| Sin riesgo | 0.804 | 0.641 | 0.713 | 64 |
| En riesgo | 0.531 | 0.722 | 0.612 | 36 |
| accuracy | 0.670 | 0.670 | 0.670 | 0.670 |
| macro avg | 0.667 | 0.681 | 0.662 | 100 |
| weighted avg | 0.706 | 0.670 | 0.677 | 100 |

## Lectura de la clase “En riesgo”

- **Precisión (0.531):** proporción de las predicciones “En riesgo” que correspondió a estudiantes realmente en esa clase.
- **Recall (0.722):** proporción de estudiantes realmente “En riesgo” que el modelo detectó.
- **F1-score (0.612):** combina precisión y recall en una sola medida.

Las métricas describen el desempeño observado en esta partición de prueba; no garantizan el mismo resultado en otros grupos.
