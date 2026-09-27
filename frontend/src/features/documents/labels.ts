import type { DocumentStatus, SourceCategory, UploadCategory } from '@/types/api'

export const CATEGORY_LABELS: Record<SourceCategory, string> = {
  job_market: 'Job adverts',
  institutional: 'University documents',
  policy: 'Policy documents',
  academic: 'Academic papers',
  nuc_core: 'NUC core',
}

/** What one document of each category is called in a sentence ("a job advert"). */
export const DOCUMENT_TYPE: Record<SourceCategory, string> = {
  job_market: 'job advert',
  institutional: 'university document',
  policy: 'policy document',
  academic: 'academic paper',
  nuc_core: 'NUC core curriculum',
}

// en-US gives "Sep 2026" (en-GB writes "Sept"), matching the labels the API builds.
const monthYearFormat = new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric' })

/** "2026-09-18" → "Sep 2026". */
export function monthYear(iso: string | null | undefined): string | null {
  return iso ? monthYearFormat.format(new Date(`${iso}T00:00:00`)) : null
}

/** Shorten long text at a word boundary, with an ellipsis. */
export function shorten(text: string, length: number): string {
  const flat = text.split(/\s+/).join(' ').trim()
  if (flat.length <= length) return flat
  // Cut at a word boundary and drop trailing punctuation before the ellipsis (no ".…").
  return `${flat
    .slice(0, length)
    .replace(/\s+\S*$/, '')
    .replace(/[\s.,;:!?…]+$/, '')}…`
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
