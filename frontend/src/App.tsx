import { useMemo, useState } from 'react'
import CsvUploader from './components/CsvUploader'
import ManualPredictionModal from './components/ManualPredictionModal'
import ResultsTable from './components/ResultsTable'
import { downloadReport, predictCsv, predictManual } from './api/client'
import type { CsvPredictionResponse, PredictionResult } from './types/prediction'
import type { StudentFeatures } from './types/student'

export default function App() {
  const [modalOpen, setModalOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [rows, setRows] = useState<PredictionResult[]>([])
  const [batch, setBatch] = useState<CsvPredictionResponse | null>(null)
  const [notice, setNotice] = useState('')
  const riskCount = useMemo(() => rows.filter((row) => row.estado_predicho === 'En riesgo').length, [rows])

  async function handleManual(student: StudentFeatures) {
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await predictManual(student)
      setRows((current) => [...current, result]); setModalOpen(false)
      setNotice('Clasificación completada. Se agregó el estudiante a la tabla.')
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo obtener la predicción.') }
    finally { setBusy(false) }
  }

  async function handleCsv(file: File) {
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await predictCsv(file)
      setBatch(result); setRows((current) => [...current, ...result.resultados])
      setNotice(`Clasificación completada. Se agregaron ${result.procesadas} estudiantes a la tabla.`)
    } catch (e) { setError(e instanceof Error ? e.message : 'No se pudo procesar el CSV.') }
    finally { setBusy(false) }
  }

  async function exportReport(format: 'csv' | 'pdf') {
    setError('')
    try { await downloadReport(format, rows, null) }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo generar el reporte.') }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#inicio" aria-label="Riesgo Académico, inicio"><span className="brand-mark">R</span><span>Riesgo<span className="brand-light"> Académico</span></span></a>
        <div className="topbar-right"><span className="privacy-dot" /> Evaluación de apoyo <span className="divider" /> Modelo supervisado</div>
      </header>

      <section className="hero" id="inicio">
        <div className="hero-copy"><span className="eyebrow">ACOMPAÑAMIENTO TEMPRANO</span><h1>Detectar a tiempo<br /><em>cambia el camino.</em></h1><p>Analiza indicadores académicos y prioriza a quién acompañar. Cada resultado es una señal para conversar, no una decisión automática.</p><button className="button button-primary" onClick={() => setModalOpen(true)}><span>＋</span> Evaluar estudiante</button></div>
        <div className="hero-graphic" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="hero-core"><span className="core-spark">✳</span><b>IA</b><small>APOYO</small></div><span className="orbital-node node-one">01</span><span className="orbital-node node-two">02</span><span className="orbital-node node-three">03</span><div className="hero-caption"><span className="caption-dot" /> PREDICCIÓN ACADÉMICA</div></div>
      </section>

      <section className="workspace">
        <div className="section-heading"><div><span className="eyebrow">FLUJO DE EVALUACIÓN</span><h2>Elige cómo empezar</h2></div><span className="steps-label"><b>01</b> / 02 · INGRESA LOS DATOS</span></div>
        <div className="input-grid">
          <article className="input-card manual-card"><div className="card-number">01</div><div className="card-icon">⌁</div><h3>Un estudiante</h3><p>Ingresa los indicadores académicos en un formulario breve.</p><button className="text-button" onClick={() => setModalOpen(true)}>Ingresar datos <span>↗</span></button></article>
          <article className="input-card csv-card"><div className="card-number">02</div><div className="card-icon csv-icon">⇧</div><h3>Un archivo CSV</h3><p>Evalúa varios estudiantes y revisa cada resultado en una tabla.</p><CsvUploader busy={busy} onFile={(file) => void handleCsv(file)} /></article>
        </div>

        {(error || notice) && <div className={`notice ${error ? 'notice-error' : 'notice-success'}`} role="status">{error || notice}</div>}
        {batch?.observaciones.map((item, index) => <div className="notice notice-info" key={`${item}-${index}`}>{item}</div>)}

        <section className="results-section">
          <div className="section-heading results-heading"><div><span className="eyebrow">RESULTADOS DEL MODELO</span><h2>Clasificaciones</h2></div>{rows.length > 0 && <div className="export-actions"><button className="button button-secondary" onClick={() => void exportReport('csv')}>↓ CSV</button><button className="button button-secondary" onClick={() => void exportReport('pdf')}>↓ PDF</button></div>}</div>
          {rows.length ? <><div className="summary-strip"><div><span>Registros procesados</span><strong>{rows.length}</strong></div><div><span>Predichos en riesgo</span><strong className="summary-risk">{riskCount}</strong></div><div><span>Sin riesgo</span><strong>{rows.length - riskCount}</strong></div><div><span>Versión del modelo</span><strong className="model-version">{rows[0].version_modelo}</strong></div></div><ResultsTable rows={rows} /><p className="table-footnote">Los indicadores reflejan cambios estimados por el modelo al comparar cada valor con una referencia del conjunto de entrenamiento. No representan causas comprobadas.</p></> : <div className="empty-state"><div className="empty-symbol">✳</div><strong>Tus resultados aparecerán aquí</strong><span>Ingresa un estudiante o carga un CSV para comenzar.</span></div>}
        </section>
      </section>

      <footer className="footer"><span>Clasificación de riesgo académico</span><span>Herramienta de apoyo para el seguimiento educativo</span></footer>
      <ManualPredictionModal open={modalOpen} busy={busy} onClose={() => setModalOpen(false)} onSubmit={handleManual} />
    </main>
  )
}
