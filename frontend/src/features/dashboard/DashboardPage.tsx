import { SystemStatusCard } from '@/features/system/SystemStatusCard'

export function DashboardPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Welcome to NLP-RS</h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          Evidence-based recommendations for the institution-designed 30% of the Computer Science
          curriculum under the NUC CCMAS framework.
        </p>
      </section>
      <div className="max-w-xl">
        <SystemStatusCard />
      </div>
    </div>
  )
}
