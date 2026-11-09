interface Props {
  busy: boolean
  onFile: (file: File) => void
}

export default function CsvUploader({ busy, onFile }: Props) {
  return (
    <label className={`upload-card ${busy ? 'is-busy' : ''}`}>
      <input type="file" accept=".csv,text/csv" disabled={busy} onChange={(event) => {
        const file = event.currentTarget.files?.[0]
        if (file) onFile(file)
        event.currentTarget.value = ''
      }} />
      <span className="upload-icon" aria-hidden="true">↑</span>
      <span className="upload-title">{busy ? 'Procesando archivo…' : 'Seleccionar archivo CSV'}</span>
      <span className="upload-caption">Un estudiante por fila · máximo 10 MB</span>
    </label>
  )
}
