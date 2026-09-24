import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiDelete, apiGet, apiPost, apiUpload } from '@/lib/api'
import type {
  DocumentDetail,
  DocumentList,
  DocumentListParams,
  DocumentSummary,
  Paginated,
  PassageSummary,
  UploadCategory,
  UploadResult,
} from '@/types/api'

import { IN_PROGRESS } from './labels'

export const documentsQueryKey = ['documents'] as const
const POLL_MS = 3000

function cleanParams<T extends object>(params: T): T {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as T
}

/** The library list; polls while any listed document is still being processed. */
export function useDocuments(params: DocumentListParams) {
  const cleaned = cleanParams(params)
  return useQuery({
    queryKey: [...documentsQueryKey, 'list', cleaned],
    queryFn: () => apiGet<DocumentList>('/documents', cleaned),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.items.some((d) => IN_PROGRESS.includes(d.processing_status))
        ? POLL_MS
        : false,
  })
}

export function useDocument(id: number) {
  return useQuery({
    queryKey: [...documentsQueryKey, 'detail', id],
    queryFn: () => apiGet<DocumentDetail>(`/documents/${id}`),
    refetchInterval: (query) =>
      query.state.data && IN_PROGRESS.includes(query.state.data.processing_status)
        ? POLL_MS
        : false,
  })
}

export function usePassages(id: number, page: number, enabled: boolean) {
  return useQuery({
    queryKey: [...documentsQueryKey, 'passages', id, page],
    queryFn: () =>
      apiGet<Paginated<PassageSummary>>(`/documents/${id}/passages`, { page, per_page: 20 }),
    placeholderData: keepPreviousData,
    enabled,
  })
}

/** Upload one file (one request per file, so each gets its own progress and result). */
export function uploadDocument(
  file: File,
  category: UploadCategory,
  onProgress?: (fraction: number) => void,
): Promise<UploadResult> {
  const form = new FormData()
  form.append('files', file)
  form.append('categories', category)
  return apiUpload<UploadResult>('/documents', form, onProgress)
}

export function useArchiveDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiPost<DocumentSummary>(`/documents/${id}/archive`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentsQueryKey }),
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiDelete<{ deleted: boolean }>(`/documents/${id}`),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: [...documentsQueryKey, 'detail', id] })
      return queryClient.invalidateQueries({ queryKey: [...documentsQueryKey, 'list'] })
    },
  })
}

/** Download URL of the original file (served through the authorised API endpoint). */
export const documentFileUrl = (id: number) => `/api/documents/${id}/file`
