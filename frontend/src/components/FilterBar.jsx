import { Search, X } from 'lucide-react'
import { TYPES, TYPE_KEYS } from './eventMeta'

export const DEFAULT_FILTERS = { q: '', from: '', to: '', order: 'desc', enabled: [...TYPE_KEYS] }

export default function FilterBar({ value, onChange }) {
  const { q, from, to, order, enabled } = value
  const set = (patch) => onChange({ ...value, ...patch })
  const toggle = (k) => set({ enabled: enabled.includes(k) ? enabled.filter((x) => x !== k) : [...enabled, k] })
  const dirty = q || from || to || enabled.length !== TYPE_KEYS.length
  const field = 'rounded border border-line bg-white px-2 py-1.5 text-sm'

  return (
    <div className="mb-6 space-y-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Event categories">
        {TYPE_KEYS.map((k) => {
          const t = TYPES[k]
          const on = enabled.includes(k)
          const Icon = t.icon
          return (
            <button
              key={k} onClick={() => toggle(k)} aria-pressed={on}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${
                on ? `${t.chip} font-medium` : 'border-dashed border-line bg-white text-ink/50 line-through'
              }`}
            >
              <Icon className="size-3.5" /> {t.plural}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search className="pointer-events-none absolute left-2 top-2 size-4 text-ink/50" />
          <input
            value={q} onChange={(e) => set({ q: e.target.value })} aria-label="Search events"
            placeholder="Search events by keyword" className={`${field} w-full px-8`}
          />
          {q && (
            <button aria-label="Clear search" onClick={() => set({ q: '' })} className="absolute right-1.5 top-1.5 rounded p-0.5 hover:bg-paper">
              <X className="size-4" />
            </button>
          )}
        </div>
        <input type="date" aria-label="From date" value={from} onChange={(e) => set({ from: e.target.value })} className={field} />
        <input type="date" aria-label="To date" value={to} onChange={(e) => set({ to: e.target.value })} className={field} />
        <select aria-label="Sort order" value={order} onChange={(e) => set({ order: e.target.value })} className={field}>
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>
        {dirty && (
          <button onClick={() => onChange(DEFAULT_FILTERS)} className="text-sm text-brand underline underline-offset-2">
            Clear filters
          </button>
        )}
      </div>
    </div>
  )
}
