import { useState } from 'react'
import { AlertCircle, CheckCircle2, Clock, FileText, Loader2, Trash2 } from 'lucide-react'
import { isActive, useDeleteRecord } from '../hooks/queries'
import { errorMessage } from '../lib/api'

const STATUS = {
  pending: { icon: Clock, text: 'Waiting in queue', tone: 'text-ink/60' },
  processing: { icon: Loader2, text: 'Reading pages and organizing events…', tone: 'text-brand', spin: true },
  completed: { icon: CheckCircle2, text: 'Processed', tone: 'text-emerald-700' },
  failed: { icon: AlertCircle, text: 'Could not process', tone: 'text-red-700' },
}

export default function ProcessingQueue({ patientId, records, isLoading }) {
  const [confirmingRecord, setConfirmingRecord] = useState(null)
  const deletion = useDeleteRecord()
  if (isLoading) return <div className="h-24 animate-pulse rounded-lg bg-line/60 motion-reduce:animate-none" />
  if (!records?.length) return null
  const active = records.some(isActive)
  const requestDelete = (record) => {
    deletion.reset()
    setConfirmingRecord(record)
  }
  const confirmDelete = () => {
    if (!confirmingRecord) return
    deletion.mutate(
      { patientId, recordId: confirmingRecord.id },
      { onSuccess: () => setConfirmingRecord(null) },
    )
  }

  return (
    <>
      <section>
        <h2 className="font-serif text-xl">Documents</h2>
        {active && (
          <p className="mb-2 mt-1 text-sm text-ink/70" aria-live="polite">
            Reading scans and analyzing text can take a minute or more per document. You can leave this page; new events will appear in the timeline.
          </p>
        )}
        <ul className="mt-2 divide-y divide-line rounded-lg border border-line bg-white">
          {records.map((r) => {
            const s = STATUS[r.status]
            const Icon = s.icon
            return (
              <li key={r.id} className="px-3 py-3">
                <div className="flex items-center gap-3 text-sm">
                  <FileText className="size-4 shrink-0 text-ink/60" />
                  <span className="min-w-0 flex-1 truncate">{r.original_filename}</span>
                  <span className={`flex shrink-0 items-center gap-1.5 ${s.tone}`}>
                    <Icon className={`size-4 ${s.spin ? 'animate-spin motion-reduce:animate-none' : ''}`} /> {s.text}
                  </span>
                  <button
                    type="button"
                    title="Delete record"
                    aria-label={`Delete ${r.original_filename}`}
                    onClick={() => requestDelete(r)}
                    className="shrink-0 rounded p-1.5 text-ink/60 hover:bg-red-50 hover:text-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
                {r.status === 'processing' && (
                  <div className="mt-2 h-1 overflow-hidden rounded bg-line">
                    <div className="h-full w-1/3 animate-pulse bg-brand motion-reduce:animate-none" />
                  </div>
                )}
                {r.status === 'failed' && r.error_message && (
                  <p className="mt-1 pl-7 text-sm text-red-700">{r.error_message}</p>
                )}
              </li>
            )
          })}
        </ul>
      </section>

      {confirmingRecord && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-4 py-6">
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-record-title"
            aria-describedby="delete-record-description"
            className="w-full max-w-md rounded-lg border border-line bg-white p-5 shadow-xl"
          >
            <h2 id="delete-record-title" className="font-serif text-xl">Delete medical record?</h2>
            <p id="delete-record-description" className="mt-2 text-sm text-ink/80">
              Are you sure you want to delete this medical record?
            </p>
            {deletion.isError && (
              <p role="alert" className="mt-3 text-sm text-red-700">
                Could not delete record: {errorMessage(deletion.error)}
              </p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={deletion.isPending}
                onClick={() => { setConfirmingRecord(null); deletion.reset() }}
                className="rounded border border-line px-3 py-2 text-sm hover:bg-paper disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletion.isPending}
                onClick={confirmDelete}
                className="rounded bg-red-700 px-3 py-2 text-sm font-medium text-white hover:bg-red-800 disabled:opacity-50"
              >
                {deletion.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
