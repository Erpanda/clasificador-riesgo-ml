import type { StudentFeatures } from '../types/student'
import type { CsvPredictionResponse, PredictionResult } from '../types/prediction'

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    return typeof body.detail === 'string' ? body.detail : 'Ocurrió un error al contactar la API.'
  } catch {
    return `La API respondió con el estado ${response.status}.`
  }
}

export async function predictManual(student: StudentFeatures): Promise<PredictionResult> {
  const { estudiante_id, ...features } = student
  const response = await fetch(`${API_BASE}/predictions/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estudiante_id, ...features }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json() as Promise<PredictionResult>
}

export async function predictCsv(file: File): Promise<CsvPredictionResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${API_BASE}/imports/csv`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json() as Promise<CsvPredictionResponse>
}

export async function downloadReport(
  format: 'csv' | 'pdf',
  results: PredictionResult[],
  batchId: string | null,
): Promise<void> {
  const response = await fetch(`${API_BASE}/reports/${format}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ carga_id: batchId, resultados: results }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = format === 'csv' ? 'clasificacion_riesgo.csv' : 'reporte_riesgo_academico.pdf'
  link.click()
  URL.revokeObjectURL(url)
}

