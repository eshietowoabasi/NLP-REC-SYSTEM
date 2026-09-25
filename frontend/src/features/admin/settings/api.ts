import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiPatch, apiPost, apiPut } from '@/lib/api'
import type {
  Paginated,
  SettingsResponse,
  SettingsUpdate,
  SkillPattern,
  SkillPatternListParams,
  SkillPatternRequest,
  StopWord,
  StopWordListParams,
} from '@/types/api'

const settingsKey = ['admin', 'settings'] as const
const patternsKey = ['admin', 'skill-patterns'] as const
const stopWordsKey = ['admin', 'stop-words'] as const

function clean<T extends object>(params: T) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  )
}

export function useSettings() {
  return useQuery({
    queryKey: settingsKey,
    queryFn: () => apiGet<SettingsResponse>('/admin/settings'),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (changes: SettingsUpdate) => apiPut<SettingsResponse>('/admin/settings', changes),
    onSuccess: (data) => {
      queryClient.setQueryData(settingsKey, { settings: data.settings })
      // New-session defaults come from these settings.
      return queryClient.invalidateQueries({ queryKey: ['sessions', 'defaults'] })
    },
  })
}

export function useSkillPatterns(params: SkillPatternListParams) {
  const cleaned = clean(params)
  return useQuery({
    queryKey: [...patternsKey, cleaned],
    queryFn: () => apiGet<Paginated<SkillPattern>>('/admin/skill-patterns', cleaned),
    placeholderData: keepPreviousData,
  })
}

export function useSaveSkillPattern(id: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SkillPatternRequest) =>
      id === null
        ? apiPost<SkillPattern>('/admin/skill-patterns', input)
        : apiPatch<SkillPattern>(`/admin/skill-patterns/${id}`, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: patternsKey }),
  })
}

export function useToggleSkillPattern() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiPatch<SkillPattern>(`/admin/skill-patterns/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: patternsKey }),
  })
}

export function useStopWords(params: StopWordListParams) {
  const cleaned = clean(params)
  return useQuery({
    queryKey: [...stopWordsKey, cleaned],
    queryFn: () => apiGet<Paginated<StopWord>>('/admin/stop-words', cleaned),
    placeholderData: keepPreviousData,
  })
}

export function useAddStopWord() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (word: string) => apiPost<StopWord>('/admin/stop-words', { word }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: stopWordsKey }),
  })
}

export function useToggleStopWord() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiPatch<StopWord>(`/admin/stop-words/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: stopWordsKey }),
  })
}
