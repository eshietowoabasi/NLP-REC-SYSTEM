import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiDelete, apiGet, apiPost } from '@/lib/api'
import type {
  CreateSessionRequest,
  DocumentList,
  DocumentSummary,
  Paginated,
  SessionDefaults,
  SessionDetail,
  SessionListParams,
  SessionSummary,
} from '@/types/api'

export const sessionsQueryKey = ['sessions'] as const
/** Session progress is polled every 2.5 s while it runs (decision 3). */
export const SESSION_POLL_MS = 2500

const isRunning = (session: { status: string }) => session.status === 'processing'

function cleanParams<T extends object>(params: T): T {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as T
}

export function useSessions(params: SessionListParams) {
  const cleaned = cleanParams(params)
  return useQuery({
    queryKey: [...sessionsQueryKey, 'list', cleaned],
    queryFn: () => apiGet<Paginated<SessionSummary>>('/sessions', cleaned),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some(isRunning) ? SESSION_POLL_MS : false),
  })
}

export function useSession(id: number) {
  return useQuery({
    queryKey: [...sessionsQueryKey, 'detail', id],
    queryFn: () => apiGet<SessionDetail>(`/sessions/${id}`),
    refetchInterval: (query) =>
      query.state.data && isRunning(query.state.data) ? SESSION_POLL_MS : false,
  })
}

export function useSessionDefaults() {
  return useQuery({
    queryKey: [...sessionsQueryKey, 'defaults'],
    queryFn: () => apiGet<SessionDefaults>('/sessions/defaults'),
  })
}

/** Every ready library document (fetched page by page), for choosing a session's inputs. */
export function useReadyDocuments() {
  return useQuery({
    queryKey: ['documents', 'ready', 'all'],
    queryFn: async () => {
      const documents: DocumentSummary[] = []
      for (let page = 1; ; page += 1) {
        const data = await apiGet<DocumentList>('/documents', {
          status: 'ready',
          per_page: 100,
          page,
        })
        documents.push(...data.items)
        if (page >= data.pagination.pages) return documents
      }
    },
  })
}

function useSessionMutation<TInput>(request: (input: TInput) => Promise<SessionDetail>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (session) => {
      queryClient.setQueryData([...sessionsQueryKey, 'detail', session.id], session)
      return queryClient.invalidateQueries({ queryKey: [...sessionsQueryKey, 'list'] })
    },
  })
}

export const useCreateSession = () =>
  useSessionMutation((input: CreateSessionRequest) => apiPost<SessionDetail>('/sessions', input))

export const useRunSession = () =>
  useSessionMutation((id: number) => apiPost<SessionDetail>(`/sessions/${id}/run`))

export const useRetrySession = () =>
  useSessionMutation((id: number) => apiPost<SessionDetail>(`/sessions/${id}/retry`))

export function useDeleteSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiDelete<{ deleted: boolean }>(`/sessions/${id}`),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: [...sessionsQueryKey, 'detail', id] })
      return queryClient.invalidateQueries({ queryKey: [...sessionsQueryKey, 'list'] })
    },
  })
}
