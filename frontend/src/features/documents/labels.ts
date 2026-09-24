import type { DocumentStatus, SourceCategory, UploadCategory } from '@/types/api'

export const CATEGORY_LABELS: Record<SourceCategory, string> = {
  job_market: 'Job market',
  institutional: 'Institutional',
  policy: 'Policy',
  academic: 'Academic',
  nuc_core: 'NUC core',
}

export const UPLOAD_CATEGORIES: readonly UploadCategory[] = [
  'job_market',
  'institutional',
  'policy',
  'academic',
]

export const CATEGORY_HINTS: Record<UploadCategory, string> = {
  job_market: 'Job adverts and skills demand reports',
  institutional: 'University and faculty documents',
  policy: 'Government and state policy documents',
  academic: 'Academic literature and curricula',
}

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: 'Queued',
  parsing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
  archived: 'Archived',
}

/** Statuses that change on their own; screens poll while any document is in one. */
export const IN_PROGRESS: readonly DocumentStatus[] = ['uploaded', 'parsing']

export const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt']
export const MAX_FILE_BYTES = 25 * 1024 * 1024

/** Client-side checks mirroring the server; the server re-checks the real content. */
export function checkFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ACCEPTED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return 'Unsupported file type. Upload PDF, DOCX or TXT files.'
  }
  if (file.size === 0) return 'The file is empty.'
  if (file.size > MAX_FILE_BYTES) return 'The file is larger than the 25 MB limit.'
  return null
}
