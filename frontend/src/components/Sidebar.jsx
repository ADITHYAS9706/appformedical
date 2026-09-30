import { useState } from 'react'
import { Activity, History, Loader2, UploadCloud, UserPlus } from 'lucide-react'
import { errorMessage } from '../lib/api'
import { useCreatePatient } from '../hooks/queries'

function NewPatientForm({ onCreated }) {
  const [first, setFirst] = useState('')
  const [last, setLast] = useState('')
  const create = useCreatePatient()
  const input = 'w-full rounded bg-white/10 px-2 py-1.5 text-sm placeholder:text-white/50'

  const submit = (e) => {
    e.preventDefault()
    create.mutate(
      { first_name: first.trim(), last_name: last.trim() },
      { onSuccess: (p) => { setFirst(''); setLast(''); onCreated(p.id) } },
    )
  }
  return (
    <form onSubmit={submit} className="mt-2 space-y-2">
      <input required className={input} placeholder="First name" value={first} onChange={(e) => setFirst(e.target.value)} />
      <input required className={input} placeholder="Last name" value={last} onChange={(e) => setLast(e.target.value)} />
      {create.isError && <p className="text-xs text-red-300">{errorMessage(create.error)}</p>}
      <button disabled={create.isPending} className="w-full rounded bg-brand px-2 py-1.5 text-sm font-medium disabled:opacity-60">
        {create.isPending ? 'Adding…' : 'Add patient'}
      </button>
    </form>
  )
}

export default function Sidebar({ view, setView, patients, patientId, onSelectPatient, activeCount }) {
  const [adding, setAdding] = useState(false)
  const nav = [
    { id: 'timeline', label: 'Timeline', icon: History },
    { id: 'upload', label: 'Upload records', icon: UploadCloud },
  ]
  return (
    <aside className="flex flex-col gap-5 bg-ink p-4 text-white md:h-full md:w-64 md:shrink-0 md:overflow-y-auto">
      <div className="flex items-center gap-2 font-serif text-xl">
        <Activity className="size-5 text-emerald-300" /> Medical Timeline
      </div>

      <div>
        <label htmlFor="patient" className="text-sm text-white/70">Patient</label>
        <select
          id="patient" value={patientId} onChange={(e) => onSelectPatient(e.target.value)}
          className="mt-1 w-full rounded bg-white/10 px-2 py-1.5 text-sm"
        >
          {patients.length === 0 && <option value="">No patients yet</option>}
          {patients.map((p) => (
            <option key={p.id} value={p.id} className="text-ink">{p.last_name}, {p.first_name}</option>
          ))}
        </select>
        <button onClick={() => setAdding((v) => !v)} className="mt-2 flex items-center gap-1 text-sm text-emerald-300">
          <UserPlus className="size-4" /> {adding ? 'Cancel' : 'New patient'}
        </button>
        {adding && <NewPatientForm onCreated={(id) => { onSelectPatient(id); setAdding(false) }} />}
      </div>

      <nav className="flex gap-1 md:flex-col">
        {nav.map(({ id, label, icon: Icon }) => (
          <button
            key={id} onClick={() => setView(id)} aria-current={view === id ? 'page' : undefined}
            className={`flex flex-1 items-center gap-2 rounded px-3 py-2 text-left text-sm md:flex-none ${
              view === id ? 'bg-white/15 font-medium' : 'text-white/75 hover:bg-white/10'
            }`}
          >
            <Icon className="size-4" /> {label}
            {id === 'upload' && activeCount > 0 && (
              <span className="ml-auto flex items-center gap-1 text-xs text-emerald-300">
                <Loader2 className="size-3 animate-spin motion-reduce:animate-none" /> {activeCount}
              </span>
            )}
          </button>
        ))}
      </nav>
    </aside>
  )
}
