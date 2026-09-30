import { useRef, useState } from 'react'
import { AlertCircle, FileText, Loader2, UploadCloud, X } from 'lucide-react'
import { errorMessage } from '../lib/api'
import { useUploadRecords } from '../hooks/queries'

const ACCEPT = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff', 'image/webp']
const MAX_MB = 25
const MAX_FILES = 20
const size = (b) => (b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.ceil(b / 1e3)} KB`)

export default function UploadDropzone({ patientId }) {
  const [files, setFiles] = useState([])
  const [rejected, setRejected] = useState([])
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const inputRef = useRef(null)
  const upload = useUploadRecords()

  const addFiles = (list) => {
    const ok = [], bad = []
    for (const f of list) {
      if (!ACCEPT.includes(f.type)) bad.push(`${f.name}: use PDF, PNG, JPG, TIFF or WebP`)
      else if (f.size > MAX_MB * 1024 * 1024) bad.push(`${f.name}: larger than ${MAX_MB} MB`)
      else ok.push(f)
    }
    setFiles((prev) => [...prev, ...ok].slice(0, MAX_FILES))
    setRejected(bad)
  }

  const submit = () =>
    upload.mutate(
      { patientId, files, onProgress: setProgress },
      { onSuccess: () => { setFiles([]); setProgress(0) } },
    )

  return (
    <section>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        role="button" tabIndex={0}
        className={`cursor-pointer rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors ${
          dragging ? 'border-brand bg-brand/5' : 'border-line bg-white hover:border-brand/60'
        }`}
      >
        <UploadCloud className="mx-auto mb-3 size-9 text-brand" />
        <p className="font-serif text-lg">Drop medical records here, or click to browse</p>
        <p className="mt-1 text-sm text-ink/70">PDF, PNG, JPG, TIFF or WebP. Up to {MAX_MB} MB each, {MAX_FILES} files at a time.</p>
        <input
          ref={inputRef} type="file" multiple hidden accept={ACCEPT.join(',')}
          onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        />
      </div>

      {rejected.length > 0 && (
        <ul role="alert" className="mt-3 space-y-1 text-sm text-red-700">
          {rejected.map((r) => <li key={r} className="flex gap-1"><AlertCircle className="mt-0.5 size-4 shrink-0" />{r}</li>)}
        </ul>
      )}

      {files.length > 0 && (
        <div className="mt-4">
          <ul className="divide-y divide-line rounded-lg border border-line bg-white">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-3 px-3 py-2 text-sm">
                <FileText className="size-4 shrink-0 text-ink/60" />
                <span className="min-w-0 flex-1 truncate">{f.name}</span>
                <span className="text-ink/60">{size(f.size)}</span>
                <button
                  aria-label={`Remove ${f.name}`} disabled={upload.isPending}
                  onClick={() => setFiles((p) => p.filter((_, j) => j !== i))}
                  className="rounded p-1 hover:bg-paper disabled:opacity-40"
                ><X className="size-4" /></button>
              </li>
            ))}
          </ul>

          {upload.isPending && (
            <div className="mt-3" aria-live="polite">
              <div className="h-1.5 overflow-hidden rounded bg-line">
                <div className="h-full bg-brand transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-sm text-ink/70">
                {progress < 100 ? `Uploading… ${progress}%` : 'Saving files…'}
              </p>
            </div>
          )}
          {upload.isError && <p role="alert" className="mt-3 text-sm text-red-700">{errorMessage(upload.error)}</p>}

          <button
            onClick={submit} disabled={upload.isPending}
            className="mt-3 inline-flex items-center gap-2 rounded bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {upload.isPending && <Loader2 className="size-4 animate-spin motion-reduce:animate-none" />}
            {upload.isPending ? 'Uploading…' : `Upload ${files.length} ${files.length === 1 ? 'file' : 'files'}`}
          </button>
        </div>
      )}
    </section>
  )
}
