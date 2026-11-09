import type { StudentFeatures } from './student'

export type RiskStatus = 'En riesgo' | 'Sin riesgo'

export interface FactorDetail {
  variable: string
  valor: string | number | null
  cambio_estimado_probabilidad: number
  interpretacion: string
}

export interface PredictionResult {
  estudiante_id: string
  datos_entrada: Partial<Record<keyof Omit<StudentFeatures, 'estudiante_id'>, number | string | null>>
  estado_predicho: RiskStatus
  probabilidad_riesgo: number
  estado_real: RiskStatus | null
  factores: FactorDetail[]
  version_modelo: string
  guardado: boolean
}

export interface CsvPredictionResponse {
  carga_id: string | null
  total_filas: number
  procesadas: number
  observaciones: string[]
  resultados: PredictionResult[]
}
