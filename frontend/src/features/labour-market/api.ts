import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  apiGet,
  apiPatch,
  apiPost,
} from '@/lib/api'
import type {
  HarvestProfile,
  HarvestRun,
  HarvestState,
} from '@/types/api'


export const harvestQueryKey = [
  'labour-market',
] as const


export function useHarvestState(
  programmeId: number | null,
) {
  return useQuery({
    enabled: Boolean(programmeId),
    queryKey: [
      ...harvestQueryKey,
      programmeId,
    ],
    queryFn: () =>
      apiGet<HarvestState>(
        `/harvest/programmes/${programmeId}`,
      ),
    refetchInterval: 3000,
  })
}


export function useSaveHarvestProfile() {
  const queryClient =
    useQueryClient()

  return useMutation({
    mutationFn: ({
      programmeId,
      profile,
    }: {
      programmeId: number
      profile: HarvestProfile
    }) =>
      apiPatch<HarvestProfile>(
        `/harvest/programmes/${programmeId}`,
        profile,
      ),

    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: [
          ...harvestQueryKey,
          variables.programmeId,
        ],
      }),
  })
}


export function useStartHarvest() {
  const queryClient =
    useQueryClient()

  return useMutation({
    mutationFn: ({
      programmeId,
      targetCount,
      pagesPerField,
    }: {
      programmeId: number
      targetCount: number
      pagesPerField: number
    }) =>
      apiPost<HarvestRun>(
        `/harvest/programmes/${programmeId}/runs`,
        {
          target_count: targetCount,
          pages_per_field:
            pagesPerField,
        },
      ),

    onSuccess: (_data, variables) =>
      queryClient.invalidateQueries({
        queryKey: [
          ...harvestQueryKey,
          variables.programmeId,
        ],
      }),
  })
}
