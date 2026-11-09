export type Participation = 'Baja' | 'Media' | 'Alta'

export interface StudentFeatures {
  estudiante_id: string
  asistencia_pct: number
  promedio_parcial: number
  horas_estudio: number
  tareas_entregadas_pct: number
  participacion_aula: Participation
  cursos_desaprobados: number
  actividad_plataforma: number
}

