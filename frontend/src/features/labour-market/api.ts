import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiPatch, apiPost } from '@/lib/api'
import type { HarvestProfile, HarvestRun, HarvestState } from '@/types/api'

import { isHarvestActive } from './labels'

export const harvestQueryKey = ['labour-market'] as const

export function useHarvestState(programmeId: number | null) {
  return useQuery({
    enabled: Boolean(programmeId),
    queryKey: [...harvestQueryKey, programmeId],
    queryFn: () => apiGet<HarvestState>(`/harvest/programmes/${programmeId}`),
    // Poll only while a collection is running or its adverts are still being prepared.
    refetchInterval: (query) => (isHarvestActive(query.state.data?.latest_run) ? 3000 : false),
  })
}

export function useSaveHarvestProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ programmeId, profile }: { programmeId: number; profile: HarvestProfile }) =>
      apiPatch<HarvestProfile>(`/harvest/programmes/${programmeId}`, profile),

    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: [...harvestQueryKey, variables.programmeId],
      }),
  })
}

export function useStartHarvest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      programmeId,
      targetCount,
      pagesPerField,
      extraTerms = [],
    }: {
      programmeId: number
      targetCount: number
      pagesPerField: number
      /** The planner's own job titles, searched as well in this run. */
      extraTerms?: string[]
    }) =>
      apiPost<HarvestRun>(`/harvest/programmes/${programmeId}/runs`, {
        target_count: targetCount,
        pages_per_field: pagesPerField,
        extra_terms: extraTerms,
      }),

    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: [...harvestQueryKey, variables.programmeId],
      }),
  })
}
