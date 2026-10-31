import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { documentsQueryKey } from '@/features/documents/api'
import { apiGet, apiPost, apiUpload } from '@/lib/api'
import type {
  NucCoreVersion,
  Programme,
  ProgrammeBenchmarkState,
} from '@/types/api'

export const programmesQueryKey = ['programmes'] as const

export function useProgrammes() {
  return useQuery({
    queryKey: [...programmesQueryKey, 'list'],
    queryFn: () => apiGet<Programme[]>('/programmes'),
  })
}

export function useProgrammeBenchmarks(
  programmeId: number | null | undefined,
) {
  return useQuery({
    enabled: Boolean(programmeId && programmeId > 0),
    queryKey: [
      ...programmesQueryKey,
      programmeId,
      'benchmarks',
    ],
    queryFn: () =>
      apiGet<ProgrammeBenchmarkState>(
        `/programmes/${programmeId}/benchmarks`,
      ),
  })
}

export function useCreateProgramme() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: {
      name: string
      discipline_code?: string | null
      faculty?: string | null
      description?: string | null
      country?: string
    }) => apiPost<Programme>('/programmes', input),

    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: programmesQueryKey,
      }),
  })
}

export function useUploadProgrammeBenchmark() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      programmeId,
      file,
      versionLabel,
      onProgress,
    }: {
      programmeId: number
      file: File
      versionLabel: string
      onProgress?: (fraction: number) => void
    }) => {
      const form = new FormData()

      form.append('file', file)
      form.append('version_label', versionLabel)

      return apiUpload<NucCoreVersion>(
        `/programmes/${programmeId}/benchmarks`,
        form,
        onProgress,
      )
    },

    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: documentsQueryKey,
      })

      return queryClient.invalidateQueries({
        queryKey: [
          ...programmesQueryKey,
          variables.programmeId,
          'benchmarks',
        ],
      })
    },
  })
}
