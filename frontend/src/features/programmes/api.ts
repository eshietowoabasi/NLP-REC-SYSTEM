import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { documentsQueryKey } from '@/features/documents/api'
import { apiGet, apiPatch, apiPost, apiUpload } from '@/lib/api'
import type {
  DisciplineList,
  NucCoreVersion,
  NucDiscipline,
  Programme,
  ProgrammeBenchmarkState,
  ProgrammeReadiness,
  ProgrammeUpdate,
} from '@/types/api'

export const programmesQueryKey = ['programmes'] as const

/** Active programmes; ``includeInactive`` adds retired ones (admins only). */
export function useProgrammes({ includeInactive = false }: { includeInactive?: boolean } = {}) {
  return useQuery({
    queryKey: [...programmesQueryKey, 'list', includeInactive],
    queryFn: () =>
      apiGet<Programme[]>('/programmes', includeInactive ? { include_inactive: true } : undefined),
  })
}

/** Programme lists also appear in New analysis (session defaults). */
function invalidateProgrammeLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ['sessions', 'defaults'] })
  return queryClient.invalidateQueries({ queryKey: programmesQueryKey })
}

export function useUpdateProgramme(programmeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (changes: ProgrammeUpdate) =>
      apiPatch<Programme>(`/programmes/${programmeId}`, changes),
    onSuccess: () => invalidateProgrammeLists(queryClient),
  })
}

export function useProgrammeBenchmarks(programmeId: number | null | undefined) {
  return useQuery({
    enabled: Boolean(programmeId && programmeId > 0),
    queryKey: [...programmesQueryKey, programmeId, 'benchmarks'],
    queryFn: () => apiGet<ProgrammeBenchmarkState>(`/programmes/${programmeId}/benchmarks`),
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
      nuc_discipline?: NucDiscipline | null
      country?: string
    }) => apiPost<Programme>('/programmes', input),

    onSuccess: () => invalidateProgrammeLists(queryClient),
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

      return apiUpload<NucCoreVersion>(`/programmes/${programmeId}/benchmarks`, form, onProgress)
    },

    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: documentsQueryKey,
      })

      return queryClient.invalidateQueries({
        queryKey: [...programmesQueryKey, variables.programmeId, 'benchmarks'],
      })
    },
  })
}

/** The 17 NUC disciplines with the size of each skills list. */
export function useDisciplines() {
  return useQuery({
    queryKey: [...programmesQueryKey, 'disciplines'],
    queryFn: () => apiGet<DisciplineList>('/programmes/disciplines'),
    staleTime: 5 * 60_000,
  })
}

/** Readiness of every programme the user may see (sidebar dots, admin list). */
export function useProgrammesReadiness() {
  return useQuery({
    queryKey: [...programmesQueryKey, 'readiness'],
    queryFn: () => apiGet<ProgrammeReadiness[]>('/programmes/readiness'),
  })
}

/** What one programme has and lacks before a review (Home checklist). */
export function useProgrammeReadiness(programmeId: number | undefined) {
  return useQuery({
    queryKey: [...programmesQueryKey, 'readiness', programmeId],
    queryFn: () => apiGet<ProgrammeReadiness>(`/programmes/${programmeId}/readiness`),
    enabled: programmeId !== undefined,
  })
}
