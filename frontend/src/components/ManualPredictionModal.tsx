import { useState, type FormEvent } from 'react'
import type { Participation, StudentFeatures } from '../types/student'

interface ManualForm {
  estudiante_id: string
  asistencia_pct: string
  promedio_parcial: string
  horas_estudio: string
  tareas_entregadas_pct: string
  participacion_aula: Participation | ''
  cursos_desaprobados: string
  actividad_plataforma: string
}

const emptyForm: ManualForm = {
  estudiante_id: '',
  asistencia_pct: '',
  promedio_parcial: '',
  horas_estudio: '',
  tareas_entregadas_pct: '',
  participacion_aula: '',
  cursos_desaprobados: '',
  actividad_plataforma: '',
}

interface Props {
  open: boolean
  busy: boolean
  onClose: () => void
  onSubmit: (student: StudentFeatures) => Promise<void>
}

export default function ManualPredictionModal({ open, busy, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<ManualForm>(emptyForm)
  if (!open) return null

  function update(field: keyof ManualForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onSubmit({
      estudiante_id: form.estudiante_id.trim(),
      asistencia_pct: Number(form.asistencia_pct),
      promedio_parcial: Number(form.promedio_parcial),
      horas_estudio: Number(form.horas_estudio),
      tareas_entregadas_pct: Number(form.tareas_entregadas_pct),
      participacion_aula: form.participacion_aula as Participation,
      cursos_desaprobados: Number(form.cursos_desaprobados),
      actividad_plataforma: Number(form.actividad_plataforma),
    })
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-heading">
          <div><span className="eyebrow">NUEVA EVALUACIÓN</span><h2 id="modal-title">Datos del estudiante</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Cerrar">×</button>
        </div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>Código del estudiante<input required value={form.estudiante_id} onChange={(e) => update('estudiante_id', e.target.value)} placeholder="EST-0001" /></label>
            <label>Asistencia (%)<input required type="number" min="0" max="100" step="0.1" value={form.asistencia_pct} onChange={(e) => update('asistencia_pct', e.target.value)} /></label>
            <label>Promedio parcial (0–20)<input required type="number" min="0" max="20" step="0.1" value={form.promedio_parcial} onChange={(e) => update('promedio_parcial', e.target.value)} /></label>
            <label>Horas de estudio / semana<input required type="number" min="0" step="0.1" value={form.horas_estudio} onChange={(e) => update('horas_estudio', e.target.value)} /></label>
            <label>Tareas entregadas (%)<input required type="number" min="0" max="100" step="0.1" value={form.tareas_entregadas_pct} onChange={(e) => update('tareas_entregadas_pct', e.target.value)} /></label>
            <label>Participación en aula<select required value={form.participacion_aula} onChange={(e) => update('participacion_aula', e.target.value)}><option value="" disabled>Selecciona una opción</option><option value="Baja">Baja</option><option value="Media">Media</option><option value="Alta">Alta</option></select></label>
            <label>Cursos desaprobados anteriormente<input required type="number" min="0" step="1" value={form.cursos_desaprobados} onChange={(e) => update('cursos_desaprobados', e.target.value)} /></label>
            <label>Accesos semanales a plataforma<input required type="number" min="0" step="1" value={form.actividad_plataforma} onChange={(e) => update('actividad_plataforma', e.target.value)} /></label>
          </div>
          <div className="modal-actions"><button className="button button-secondary" type="button" onClick={onClose}>Cancelar</button><button className="button button-primary" disabled={busy}>{busy ? 'Calculando…' : 'Obtener predicción'}</button></div>
        </form>
      </section>
    </div>
  )
}
