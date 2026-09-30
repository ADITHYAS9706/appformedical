import { useState } from 'react'
import { Activity, AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react'
import { api, errorMessage } from '../lib/api'

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [role, setRole] = useState('patient')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'register') {
        await api.post('/auth/register', { email, password, role })
      }
      const { data } = await api.post('/auth/login', { email, password })
      sessionStorage.setItem('accessToken', data.access_token)
      onAuthenticated()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-paper px-4 py-10">
      <main className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-2 font-serif text-2xl text-ink">
          <Activity className="size-6 text-emerald-700" /> Medical Timeline
        </div>
        <h1 className="font-serif text-xl">{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
        <div className="mt-4 flex gap-2 border-b border-line" role="tablist" aria-label="Account action">
          {[
            ['login', 'Sign in'],
            ['register', 'Create account'],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mode === id}
              onClick={() => { setMode(id); setError('') }}
              className={`border-b-2 px-2 py-2 text-sm ${mode === id ? 'border-brand font-medium text-ink' : 'border-transparent text-ink/60 hover:text-ink'}`}
            >
              {label}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="mt-5 space-y-4">
          {mode === 'register' && (
            <label className="block text-sm">
              Account type
              <select
                value={role}
                onChange={(event) => setRole(event.target.value)}
                className="mt-1 w-full rounded border border-line bg-white px-3 py-2"
              >
                <option value="patient">Patient</option>
                <option value="caregiver">Caregiver</option>
              </select>
            </label>
          )}
          <label className="block text-sm">
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded border border-line bg-white px-3 py-2"
            />
          </label>
          <div className="block text-sm">
            <label htmlFor="auth-password">Password</label>
            <div className="relative mt-1">
            <input
              id="auth-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={mode === 'login' ? 1 : 12}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded border border-line bg-white px-3 py-2 pr-11"
            />
              <button
                type="button"
                title={showPassword ? 'Hide password' : 'Show password'}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
                className="absolute inset-y-0 right-1 grid w-9 place-items-center rounded text-ink/60 hover:bg-paper hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            {mode === 'register' && <span className="mt-1 block text-xs text-ink/60">Use at least 12 characters.</span>}
          </div>
          {error && <p role="alert" className="flex items-start gap-2 text-sm text-red-700"><AlertCircle className="mt-0.5 size-4 shrink-0" />{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="inline-flex w-full items-center justify-center gap-2 rounded bg-brand px-4 py-2 font-medium text-white disabled:opacity-60"
          >
            {busy && <Loader2 className="size-4 animate-spin motion-reduce:animate-none" />}
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </main>
    </div>
  )
}