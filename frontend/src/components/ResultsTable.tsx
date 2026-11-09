import type { PredictionResult } from '../types/prediction'

const variableNames: Record<string, string> = {
  asistencia_pct: 'Asistencia', promedio_parcial: 'Promedio parcial', horas_estudio: 'Horas de estudio',
  tareas_entregadas_pct: 'Tareas entregadas', participacion_aula: 'Participación',
  cursos_desaprobados: 'Cursos desaprobados', actividad_plataforma: 'Accesos a plataforma',
}

interface Props { rows: PredictionResult[] }

export default function ResultsTable({ rows }: Props) {
  if (!rows.length) return null
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Estudiante</th><th>Predicción</th><th>Prob. de riesgo</th><th>Estado conocido</th><th>Indicadores del modelo</th></tr></thead>
        <tbody>{rows.map((row, index) => (
          <tr key={`${row.estudiante_id}-${index}`}>
            <td className="student-code">{row.estudiante_id}</td>
            <td><span className={`status-pill ${row.estado_predicho === 'En riesgo' ? 'status-risk' : 'status-safe'}`}><i />{row.estado_predicho}</span></td>
            <td><div className="probability"><span>{(row.probabilidad_riesgo * 100).toFixed(1)}%</span><div className="progress"><i style={{ width: `${Math.max(0, Math.min(100, row.probabilidad_riesgo * 100))}%` }} /></div></div></td>
            <td>{row.estado_real ? <span className="known-status">{row.estado_real}</span> : <span className="muted">No informado</span>}</td>
            <td><div className="factor-list">{row.factores.length ? row.factores.slice(0, 2).map((factor) => <span key={factor.variable} title={factor.interpretacion}>{variableNames[factor.variable] ?? factor.variable}<b className={factor.cambio_estimado_probabilidad >= 0 ? 'effect-up' : 'effect-down'}>{factor.cambio_estimado_probabilidad >= 0 ? '+' : ''}{(factor.cambio_estimado_probabilidad * 100).toFixed(1)} pp</b></span>) : <span className="muted">Sin diferencias destacables</span>}</div></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}
