import { useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import AuthScreen from './components/AuthScreen'
import DisclaimerBanner from './components/DisclaimerBanner'
import Sidebar from './components/Sidebar'
import Timeline from './components/Timeline'
import UploadDropzone from './components/UploadDropzone'
import ProcessingQueue from './components/ProcessingQueue'
import { errorMessage } from './lib/api'
import { isActive, useCurrentUser, usePatients, useRecords } from './hooks/queries'

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('accessToken') ?? '')
  if (!token) return <AuthScreen onAuthenticated={() => setToken(sessionStorage.getItem('accessToken') ?? '')} />
  return <AuthenticatedApp key={token} onLogout={() => setToken('')} />
}

function AuthenticatedApp({ onLogout }) {
  const queryClient = useQueryClient()
  const [view, setView] = useState('timeline')
  const [storedId, setStoredId] = useState(() => localStorage.getItem('patientId') ?? '')
  const currentUser = useCurrentUser()
  const patients = usePatients()

  const patient = patients.data?.find((p) => p.id === storedId)
  const selectPatient = (id) => { setStoredId(id); localStorage.setItem('patientId', id) }
  useEffect(() => {
    if (patients.data?.length && !patient) selectPatient(patients.data[0].id)
  }, [patients.data, patient])

  const records = useRecords(patient?.id)
  const activeCount = records.data?.filter(isActive).length ?? 0
  const isClinician = currentUser.data?.role === 'clinician'
  const logout = () => {
    sessionStorage.removeItem('accessToken')
    localStorage.removeItem('patientId')
    queryClient.clear()
    onLogout()
  }

  if (currentUser.isError) {
    return (
      <div className="grid min-h-screen place-items-center bg-paper px-4">
        <div className="max-w-md rounded-lg border border-line bg-white p-6 text-center">
          <p role="alert" className="text-sm text-red-700">{errorMessage(currentUser.error)}</p>
          <button onClick={logout} className="mt-4 rounded bg-brand px-4 py-2 text-sm font-medium text-white">Sign in again</button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <DisclaimerBanner />
      <div className="min-h-0 flex-1 overflow-y-auto md:flex md:overflow-hidden">
        <Sidebar
          view={view} setView={setView}
          patients={patients.data ?? []} patientId={patient?.id ?? ''} onSelectPatient={selectPatient}
          activeCount={activeCount} currentUser={currentUser.data} onLogout={logout}
        />
        <main className="min-w-0 flex-1 px-4 py-6 md:h-full md:overflow-y-auto md:px-10 md:py-8">
          <div className="mx-auto max-w-3xl">
            {patients.isError ? (
              <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                {errorMessage(patients.error)}
              </p>
            ) : !patient ? (
              <div className="py-24 text-center">
                <UserPlus className="mx-auto mb-3 size-8 text-brand" />
                <h1 className="font-serif text-2xl">
                  {patients.isLoading ? 'Loading…' : 'Add a patient to get started'}
                </h1>
                {!patients.isLoading && (
                  <p className="mt-1 text-sm text-ink/70">
                    {isClinician
                      ? 'No patient profiles have been shared with this clinician account.'
                      : 'Use “New patient” in the sidebar, then upload their records.'}
                  </p>
                )}
              </div>
            ) : (
              <>
                <h1 className="font-serif text-3xl font-medium">{patient.first_name} {patient.last_name}</h1>
                <p className="mb-6 mt-1 text-sm text-ink/70">
                  {view === 'timeline'
                    ? 'Events organized from uploaded records.'
                    : 'PDFs and images are read and organized automatically.'}
                </p>
                {view === 'timeline' ? (
                  <Timeline
                    patientId={patient.id}
                    activeCount={activeCount}
                    hasCompletedRecords={records.data?.some((record) => record.status === 'completed') ?? false}
                  />
                ) : (
                  <div className="space-y-8">
                    {!isClinician && <UploadDropzone patientId={patient.id} />}
                    <ProcessingQueue patientId={patient.id} records={records.data} isLoading={records.isLoading} />
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
