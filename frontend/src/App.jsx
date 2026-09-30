import { useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'
import DisclaimerBanner from './components/DisclaimerBanner'
import Sidebar from './components/Sidebar'
import Timeline from './components/Timeline'
import UploadDropzone from './components/UploadDropzone'
import ProcessingQueue from './components/ProcessingQueue'
import { errorMessage } from './lib/api'
import { isActive, usePatients, useRecords } from './hooks/queries'

export default function App() {
  const [view, setView] = useState('timeline')
  const [storedId, setStoredId] = useState(() => localStorage.getItem('patientId') ?? '')
  const patients = usePatients()

  const patient = patients.data?.find((p) => p.id === storedId)
  const selectPatient = (id) => { setStoredId(id); localStorage.setItem('patientId', id) }
  useEffect(() => {
    if (patients.data?.length && !patient) selectPatient(patients.data[0].id)
  }, [patients.data, patient])

  const records = useRecords(patient?.id)
  const activeCount = records.data?.filter(isActive).length ?? 0

  return (
    <div className="flex h-screen flex-col">
      <DisclaimerBanner />
      <div className="min-h-0 flex-1 overflow-y-auto md:flex md:overflow-hidden">
        <Sidebar
          view={view} setView={setView}
          patients={patients.data ?? []} patientId={patient?.id ?? ''} onSelectPatient={selectPatient}
          activeCount={activeCount}
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
                  <p className="mt-1 text-sm text-ink/70">Use “New patient” in the sidebar, then upload their records.</p>
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
                    <UploadDropzone patientId={patient.id} />
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
