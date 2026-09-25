import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from '@/lib/api'
import type {
  CourseMapping,
  DecisionRequest,
  EntityResults,
  KeywordResults,
  MappingRequest,
  ProposedCurriculum,
  Recommendation,
  RecommendationDetail,
  RecommendationEditRequest,
  RecommendationList,
  RecommendationListParams,
  SimilarityResults,
  TopicResults,
} from '@/types/api'

export const reviewQueryKey = ['review'] as const

/* ------------------------------------------------------------ evidence results */

type ResultName = 'keywords' | 'entities' | 'topics' | 'similarity'
interface ResultTypes {
  keywords: KeywordResults
  entities: EntityResults
  topics: TopicResults
  similarity: SimilarityResults
}

/** Stored NLP results of a completed session (they never change, so they are cached). */
export function useSessionResult<N extends ResultName>(sessionId: number, name: N, enabled = true) {
  return useQuery({
    queryKey: [...reviewQueryKey, 'results', sessionId, name],
    queryFn: () => apiGet<ResultTypes[N]>(`/sessions/${sessionId}/${name}`),
    staleTime: Infinity,
    enabled,
  })
}

/* ------------------------------------------------------------ recommendations */

export function useRecommendations(sessionId: number, params: RecommendationListParams) {
  const query = {
    decision: params.decision === 'all' ? undefined : params.decision,
    hide_duplicates: params.hide_duplicates ? 'true' : undefined,
  }
  return useQuery({
    queryKey: [...reviewQueryKey, 'recommendations', sessionId, query],
    queryFn: () => apiGet<RecommendationList>(`/sessions/${sessionId}/recommendations`, query),
    placeholderData: keepPreviousData,
  })
}

export function useRecommendation(id: number) {
  return useQuery({
    queryKey: [...reviewQueryKey, 'recommendation', id],
    queryFn: () => apiGet<RecommendationDetail>(`/recommendations/${id}`),
  })
}

export function useCurriculum(sessionId: number) {
  return useQuery({
    queryKey: [...reviewQueryKey, 'curriculum', sessionId],
    queryFn: () => apiGet<ProposedCurriculum>(`/sessions/${sessionId}/curriculum`),
  })
}

/**
 * Keeps cached copies in step after a change to one recommendation: the detail is patched
 * in place (evidence and mapping kept) and every list and curriculum is refetched.
 */
function useRecommendationSync() {
  const queryClient = useQueryClient()
  return (updated: Partial<RecommendationDetail> & { id: number }) => {
    queryClient.setQueryData<RecommendationDetail>(
      [...reviewQueryKey, 'recommendation', updated.id],
      (current) => (current ? { ...current, ...updated } : current),
    )
    void queryClient.invalidateQueries({ queryKey: [...reviewQueryKey, 'recommendations'] })
    void queryClient.invalidateQueries({ queryKey: [...reviewQueryKey, 'curriculum'] })
  }
}

export function useEditRecommendation(id: number) {
  const sync = useRecommendationSync()
  return useMutation({
    mutationFn: (input: RecommendationEditRequest) =>
      apiPatch<Recommendation>(`/recommendations/${id}`, input),
    onSuccess: sync,
  })
}

export function useDecide() {
  const sync = useRecommendationSync()
  return useMutation({
    mutationFn: ({ id, ...input }: DecisionRequest & { id: number }) =>
      apiPatch<Recommendation>(`/recommendations/${id}/decision`, input),
    onSuccess: sync,
  })
}

/* --------------------------------------------------------------------- mapping */

export function useSaveMapping(recommendationId: number, mappingId: number | null) {
  const sync = useRecommendationSync()
  return useMutation({
    mutationFn: (input: MappingRequest) =>
      mappingId === null
        ? apiPost<CourseMapping>(`/recommendations/${recommendationId}/mapping`, input)
        : apiPut<CourseMapping>(`/mappings/${mappingId}`, input),
    onSuccess: (mapping) => sync({ id: recommendationId, mapping, has_mapping: true }),
  })
}

export function useDeleteMapping(recommendationId: number) {
  const sync = useRecommendationSync()
  return useMutation({
    mutationFn: (mappingId: number) => apiDelete<{ deleted: boolean }>(`/mappings/${mappingId}`),
    onSuccess: () => sync({ id: recommendationId, mapping: null, has_mapping: false }),
  })
}
