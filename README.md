# Clasificador de riesgo académico

Aplicación académica para estimar si un estudiante está **En riesgo** o **Sin riesgo** con datos disponibles durante el ciclo. La predicción sirve como apoyo para seguimiento; no sustituye la evaluación ni la decisión de docentes.

## Tecnologías

- Frontend: React, TypeScript y Vite.
- API y procesamiento: Python y FastAPI.
- Modelo activo: Árbol de Decisión de scikit-learn basado en el entrenamiento de X e y de un integrante del equipo.
- Persistencia: Supabase (PostgreSQL).
- Despliegue previsto: frontend estático y API en Render.

## Estructura

```text
frontend/                     Aplicación React
backend/app/                  API, esquemas, modelo y servicios
backend/scripts/              Auditoría, entrenamiento y evaluación
backend/data/                 X e y preparados para entrenar (generados por la auditoría)
backend/reports/              Gráficos que genera el entrenamiento
backend/app/artifacts/project_model/  Modelo activo, metadatos y métricas
backend/reports/                      Gráficos del modelo activo
backend/alternatives/our_model/       Modelo y entrenamiento anterior, conservados para mejoras futuras
supabase/migrations/          Esquema SQL
```

## Preparación local

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

Configura `SUPABASE_URL` y `SUPABASE_SECRET_KEY` en `.env` para persistir cargas y predicciones. Ejecuta el SQL de `supabase/migrations/001_create_tables.sql` en el editor SQL de Supabase. La clave secreta se usa solo en FastAPI; nunca la copies al frontend.

### Auditar el dataset y entrenar

La auditoría imprime un reporte por secciones en consola: estructura, faltantes, duplicados, distribución de clases y categorías, resumen numérico y validación de rangos. Si los datos pasan la validación, prepara `backend/data/X_predictoras.csv` y `backend/data/y_objetivo.csv` para el entrenamiento; no modifica el CSV original.

```powershell
Set-Location backend
python -m scripts.train_model
```

El entrenamiento reproduce la comparación de `Entrenamiento.py`: Árbol de Decisión, Random Forest y KNN (con escalado), con `random_state=42` y la misma división estratificada 80/20. Selecciona el de mayor exactitud en la prueba, como el script del compañero. `participacion_aula` se codifica como Baja=0, Media=1 y Alta=2; el objetivo se interpreta como 0=Sin riesgo y 1=En riesgo. Guarda el modelo seleccionado, sus metadatos y las métricas de prueba en `backend/app/artifacts/project_model/`; genera imágenes y el reporte explicativo `reporte_modelo.md` en `backend/reports/`. Si las credenciales de Supabase están configuradas, también registra las métricas de la evaluación en `evaluaciones_modelo`. Los artefactos y el script de nuestros modelos anteriores están conservados en `backend/alternatives/our_model/` y no se usan en la API.

El reporte Markdown también puede regenerarse por separado, sin volver a entrenar los modelos:

```powershell
Set-Location backend
python -m scripts.generate_model_report
```

Para volver a entrenar nuestros modelos anteriores de forma independiente, desde `backend/` ejecuta `python -m alternatives.our_model.train_our_models`.

**Antes de interpretar resultados**, documenten el criterio que originó `riesgo_academico`. Un modelo entrenado con etiquetas simuladas aprende esa regla simulada; no demuestra que las predicciones representen riesgo real.

### Iniciar API

Desde `backend/`:

```powershell
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: <http://localhost:8000/docs>. La API informa `model_ready: false` hasta que se genere el artefacto. Para predecir también debe estar configurada Supabase si se espera que los resultados queden guardados.

### Iniciar frontend

En otra terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Vite mostrará la dirección local. Cambia `VITE_API_URL` cuando despliegues la API.

## Contrato del CSV

El archivo de entrada necesita `estudiante_id` y estas variables: `asistencia_pct`, `promedio_parcial`, `horas_estudio`, `tareas_entregadas_pct`, `participacion_aula`, `cursos_desaprobados` y `actividad_plataforma`. `riesgo_academico` es opcional: si viene, se guarda como estado conocido para comparación, pero nunca se entrega al modelo como entrada. Se aceptan hasta 5,000 filas y archivos de hasta 10 MB.

La interfaz ofrece una predicción manual y carga de CSV, presenta probabilidad, estado conocido si lo hay, factores de sensibilidad estimada, y permite descargar un CSV de resultados y un PDF resumen. Si faltan variables predictoras en un CSV, el pipeline usa medianas/modas aprendidas únicamente del conjunto de entrenamiento; el dato original vacío se conserva como nulo en Supabase y la fila queda señalada en las observaciones.

## Base de datos

Las tablas `cargas_csv`, `registros_academicos`, `clasificaciones`, `detalles_clasificacion` y `evaluaciones_modelo` conservan lotes, datos académicos, predicciones, explicaciones y métricas generales. Se registra una fila por carga, no se sobrescribe el historial de un estudiante.

## Despliegue

En Render, configura el directorio raíz del servicio de API en `backend/`, comando de instalación `pip install -r requirements.txt` y comando de inicio `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Incluye `backend/app/artifacts/project_model/modelo_riesgo_api.pkl` y `model_metadata.json` en el despliegue. Define `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `MODEL_PATH`, `MODEL_METADATA_PATH` y `FRONTEND_ORIGIN` como variables del backend. En el frontend, establece `VITE_API_URL` con la URL del API.

La interfaz y la API no tienen un flujo de inicio de sesión en este alcance. No publiques el servicio con datos reales de estudiantes hasta configurar una restricción de acceso adecuada al entorno académico.
