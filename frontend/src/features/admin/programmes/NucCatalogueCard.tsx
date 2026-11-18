import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Library, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { programmesQueryKey } from '@/features/programmes/api'
import { apiGet, apiPost } from '@/lib/api'

interface CatalogueStatus {
  available: number
  ready: number
  processing: number
  missing: number
}

const catalogueKey = [...programmesQueryKey, 'catalogue'] as const

/**
 * The NUC programmes shipped with SkillBridge (sections of the CCMAS 2023 documents): one click
 * creates every programme and loads its NUC core in the background.
 */
export function NucCatalogueCard() {
  const queryClient = useQueryClient()
  const status = useQuery({
    queryKey: catalogueKey,
    queryFn: () => apiGet<CatalogueStatus>('/programmes/catalogue'),
    refetchInterval: (query) => ((query.state.data?.processing ?? 0) > 0 ? 5000 : false),
  })
  const load = useMutation({
    mutationFn: () => apiPost<CatalogueStatus>('/programmes/catalogue/load'),
    onSuccess: () => {
      toast.success('Loading the NUC programmes. This takes a few minutes.')
      // The programmes appear as the background job creates them.
      const refresh = () => void queryClient.invalidateQueries({ queryKey: programmesQueryKey })
      setTimeout(refresh, 4000)
      setTimeout(refresh, 15000)
    },
    onError: (error) => toast.error(error.message),
  })

  const data = status.data
  if (!data || data.available === 0) return null
  const done = data.ready === data.available
  return (
    <section
      aria-labelledby="catalogue-title"
      className="flex flex-wrap items-center gap-4 rounded-[14px] border border-line bg-white px-5 py-4"
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-sand-deep text-terracotta">
        {done ? <Check aria-hidden="true" /> : <Library aria-hidden="true" />}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 id="catalogue-title" className="text-sm font-extrabold text-ink">
          NUC CCMAS programmes
        </h3>
        <p className="text-[13px] text-body-soft">
          <span className="num font-semibold text-ink">{data.ready}</span> of{' '}
          <span className="num">{data.available}</span> programmes from the Computing, Engineering
          and Technology, and Allied Health Sciences CCMAS have their NUC core loaded
          {data.processing > 0 && (
            <>
              ; <span className="num">{data.processing}</span> being processed
            </>
          )}
          .
        </p>
        {data.processing > 0 && (
          <Progress
            value={(data.ready / data.available) * 100}
            aria-label="NUC programmes loaded"
            className="h-1.5 max-w-md"
          />
        )}
      </div>
      {!done && (
        <Button onClick={() => load.mutate()} disabled={load.isPending || data.processing > 0}>
          {load.isPending || data.processing > 0 ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <Library aria-hidden="true" />
          )}
          {data.processing > 0 ? 'Loading…' : `Load all ${data.missing} NUC programmes`}
        </Button>
      )}
    </section>
  )
}
