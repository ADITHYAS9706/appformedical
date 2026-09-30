import { ShieldAlert } from 'lucide-react'

// Permanent by design: no dismiss control, always rendered above everything else.
export default function DisclaimerBanner() {
  return (
    <div role="note" className="flex shrink-0 items-start gap-2 border-b-2 border-amber-400 bg-amber-100 px-4 py-2.5 text-sm font-medium text-amber-950">
      <ShieldAlert className="mt-0.5 size-5 shrink-0" />
      <p>
        This tool organizes records for informational review only and does not provide medical diagnoses or treatment recommendations.
      </p>
    </div>
  )
}
