# Auditoría inicial del dataset

Archivo revisado: `G1_Dataset_500_Riesgo_Academico.csv`. Se revisaron los 500 registros.

## Resultado

- 500 filas y 9 columnas.
- 0 valores vacíos en cualquiera de las columnas.
- 0 códigos de estudiante repetidos.
- 0 filas duplicadas exactas.
- Etiquetas: 182 `En riesgo` y 318 `Sin riesgo`.
- Participación: 145 `Baja`, 243 `Media` y 112 `Alta`.
- No se detectaron etiquetas o categorías de participación fuera de las clases esperadas.
- No se detectaron valores fuera de rango para asistencia (0–100), promedio parcial (0–20) o tareas entregadas (0–100).

## Rangos observados

| Variable | Mínimo | Máximo | Media |
|---|---:|---:|---:|
| `asistencia_pct` | 25 | 98 | 69.84 |
| `promedio_parcial` | 4.8 | 20 | 13.38 |
| `horas_estudio` | 0.2 | 15.4 | 4.23 |
| `tareas_entregadas_pct` | 22 | 100 | 69.62 |
| `cursos_desaprobados` | 0 | 4 | 0.95 |
| `actividad_plataforma` | 0 | 18 | 7.93 |

## Pendiente antes de interpretar el modelo

El archivo contiene la etiqueta `riesgo_academico`, pero no documenta en sí mismo quién la asignó ni con qué regla. El equipo debe confirmar si las etiquetas son históricas o simuladas y describir el criterio de asignación. Las métricas del modelo medirán cuánto reproduce esas etiquetas; no prueban por sí solas que el riesgo futuro real esté bien identificado.
