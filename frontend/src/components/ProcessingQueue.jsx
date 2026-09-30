import { AlertCircle, CheckCircle2, Clock, FileText, Loader2 } from 'lucide-react'
import { isActive } from '../hooks/queries'

const STATUS = {
  pending: { icon: Clock, text: 'Waiting in queue', tone: 'text-ink/60' },
  processing: { icon: Loader2, text: 'Reading pages and organizing events…', tone: 'text-brand', spin: true },
  completed: { icon: CheckCircle2, text: 'Added to timeline', tone: 'text-emerald-700' },
  failed: { icon: AlertCircle, text: 'Could not process', tone: 'text-red-700' },
}

export default function ProcessingQueue({ records, isLoading }) {
  if (isLoading) return <div className="h-24 animate-pulse rounded-lg bg-line/60 motion-reduce:animate-none" />
  if (!records?.length) return null
  const active = records.some(isActive)

  return (
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
  )
}
