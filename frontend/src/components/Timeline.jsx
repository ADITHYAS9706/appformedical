import { useEffect, useState } from 'react'
import { AlertCircle, Building2, Loader2 } from 'lucide-react'
import { errorMessage } from '../lib/api'
import { useEvents } from '../hooks/queries'
import FilterBar, { DEFAULT_FILTERS } from './FilterBar'
import SummaryPanel from './SummaryPanel'
import { TYPES, TYPE_KEYS, fmtDate, fmtMonth } from './eventMeta'

function useDebounced(value, ms = 350) {
  const [v, setV] = useState(value)
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t) }, [value, ms])
  return v
}

/** Items arrive already sorted by the API; keep that order and split into month groups. */
function groupByMonth(items) {
  const groups = []
  for (const ev of items) {
    const key = ev.event_date.slice(0, 7)
    const last = groups[groups.length - 1]
    if (last?.key === key) last.items.push(ev)
    else groups.push({ key, items: [ev] })
  }
  return groups
}

function EventRow({ ev, flashing }) {
  const t = TYPES[ev.event_type]
  const Icon = t.icon
  return (
    <li id={`event-${ev.id}`} className="relative pb-6 pl-8 last:pb-2">
      <span className={`absolute -left-3 top-1 grid size-6 place-items-center rounded-full text-white ring-4 ring-paper ${t.dot}`}>
        <Icon className="size-3.5" />
      </span>
      <div className={`-ml-2 rounded px-2 py-1 transition-colors duration-500 ${flashing ? 'bg-amber-100' : ''}`}>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <time className="font-medium tabular-nums">{fmtDate(ev.event_date)}</time>
          <span className={`rounded-full border px-2 py-0.5 text-xs ${t.chip}`}>{t.label}</span>
        </div>
        <h3 className="mt-1 font-serif text-lg leading-snug">{ev.title ?? t.label}</h3>
        <p className="mt-0.5 max-w-prose text-sm leading-relaxed text-ink/80">{ev.description}</p>
        {(ev.provider || ev.source_page) && (
          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 text-xs text-ink/60">
            {ev.provider && <span className="flex items-center gap-1"><Building2 className="size-3.5" />{ev.provider}</span>}
            {ev.source_page && <span>Page {ev.source_page} of source</span>}
          </p>
        )}
      </div>
    </li>
  )
}

export default function Timeline({ patientId, activeCount, hasCompletedRecords }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [flash, setFlash] = useState([])
  useEffect(() => setFilters(DEFAULT_FILTERS), [patientId])

  const dq = useDebounced(filters.q.trim())
  const noneOn = filters.enabled.length === 0
  const badRange = !!(filters.from && filters.to && filters.from > filters.to)
  const events = useEvents(
    patientId,
    {
      event_type: filters.enabled.length === TYPE_KEYS.length ? undefined : filters.enabled,
      q: dq.length >= 2 ? dq : undefined, // backend requires 2+ characters
      date_from: filters.from || undefined,
      date_to: filters.to || undefined,
      order: filters.order,
    },
    !noneOn && !badRange,
  )

  const items = events.data?.pages.flatMap((p) => p.items) ?? []
  const total = events.data?.pages[0]?.total ?? 0
  const filtered = !!(dq || filters.from || filters.to || filters.enabled.length !== TYPE_KEYS.length)

  const jumpTo = (ids) => {
    setFlash(ids)
    document.getElementById(`event-${ids.find((id) => document.getElementById(`event-${id}`))}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => setFlash([]), 2500)
  }

  let body
  if (noneOn) body = <Empty title="All categories are off" text="Turn on at least one category to see events." />
  else if (badRange) body = <Empty title="Check the date range" text="The start date is after the end date." />
  else if (events.isLoading) {
    body = (
      <div className="space-y-6">
        {[0, 1, 2, 3].map((i) => <div key={i} className="h-16 animate-pulse rounded bg-line/60 motion-reduce:animate-none" />)}
      </div>
    )
  } else if (events.isError) {
    body = <p role="alert" className="flex items-center gap-2 text-sm text-red-700"><AlertCircle className="size-4" />{errorMessage(events.error)}</p>
  } else if (items.length === 0) {
    const text = filtered
      ? 'Try removing a filter.'
      : hasCompletedRecords
        ? 'No dated events were extracted. Check that the processed records contain readable dates and medical event details.'
        : 'Upload records to build this patient’s timeline.'
    body = <Empty title="No events found" text={text} />
  } else {
    body = (
      <>
        <p className="mb-2 text-sm text-ink/60" aria-live="polite">
          Showing {items.length} of {total} {total === 1 ? 'event' : 'events'}
        </p>
        <div className={events.isPlaceholderData ? 'opacity-60' : ''}>
          {groupByMonth(items).map((g) => (
            <section key={g.key} aria-label={fmtMonth(g.key)}>
              <h2 className="sticky top-0 z-10 bg-paper/95 py-2 font-serif text-xl backdrop-blur">
                {fmtMonth(g.key)}
                <span className="ml-2 font-sans text-sm text-ink/50">
                  {g.items.length} {g.items.length === 1 ? 'event' : 'events'}
                </span>
              </h2>
              <ol className="ml-3 mt-1 border-l border-line">
                {g.items.map((ev) => <EventRow key={ev.id} ev={ev} flashing={flash.includes(ev.id)} />)}
              </ol>
            </section>
          ))}
        </div>
        {events.hasNextPage && (
          <button
            onClick={() => events.fetchNextPage()} disabled={events.isFetchingNextPage}
            className="mt-4 inline-flex items-center gap-2 rounded border border-line bg-white px-4 py-2 text-sm hover:border-ink/30 disabled:opacity-60"
          >
            {events.isFetchingNextPage && <Loader2 className="size-4 animate-spin motion-reduce:animate-none" />}
            Load more
          </button>
        )}
      </>
    )
  }

  return (
    <div>
      {activeCount > 0 && (
        <p className="mb-5 flex items-center gap-2 text-sm text-brand" aria-live="polite">
          <Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
          {activeCount} {activeCount === 1 ? 'document is' : 'documents are'} still being analyzed. New events will appear here.
        </p>
      )}
      <SummaryPanel patientId={patientId} from={filters.from} to={filters.to} disabled={badRange} onJump={jumpTo} />
      <FilterBar value={filters} onChange={setFilters} />
      {body}
    </div>
  )
}

function Empty({ title, text }) {
  return (
    <div className="py-16 text-center text-ink/70">
      <h2 className="font-serif text-xl text-ink">{title}</h2>
      <p className="mt-1 text-sm">{text}</p>
    </div>
  )
}
