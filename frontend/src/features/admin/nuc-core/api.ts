import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { documentsQueryKey } from '@/features/documents/api'
import { IN_PROGRESS } from '@/features/documents/labels'
import { apiGet, apiUpload } from '@/lib/api'
import type { NucCoreState, NucCoreVersion } from '@/types/api'

export const nucCoreQueryKey = ['nuc-core'] as const
const POLL_MS = 3000

const processing = (version: NucCoreVersion | null) =>
  version !== null && IN_PROGRESS.includes(version.document.processing_status)

/** Active and latest version; polls while the latest upload is still being processed. */
export function useNucCore() {
  return useQuery({
    queryKey: [...nucCoreQueryKey, 'current'],
    queryFn: () => apiGet<NucCoreState>('/nuc-core'),
    refetchInterval: (query) => (processing(query.state.data?.latest ?? null) ? POLL_MS : false),
  })
}

export function useNucCoreVersions() {
  return useQuery({
    queryKey: [...nucCoreQueryKey, 'versions'],
    queryFn: () => apiGet<NucCoreVersion[]>('/nuc-core/versions'),
    refetchInterval: (query) => (query.state.data?.some(processing) ? POLL_MS : false),
  })
}

export function useUploadNucCore() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      file,
      versionLabel,
      onProgress,
    }: {
      file: File
      versionLabel: string
      onProgress?: (fraction: number) => void
    }) => {
      const form = new FormData()
      form.append('file', file)
      form.append('version_label', versionLabel)
      return apiUpload<NucCoreVersion>('/nuc-core', form, onProgress)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: documentsQueryKey })
      return queryClient.invalidateQueries({ queryKey: nucCoreQueryKey })
    },
  })
}
