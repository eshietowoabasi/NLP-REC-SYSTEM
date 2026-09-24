export function score(value, digits = 2) {
  return typeof value === 'number' ? value.toFixed(digits) : '–'
}

export function percent(value) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '–'
}

export function dateTime(iso) {
  if (!iso) return '–'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '–' : d.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

export function fileSize(bytes) {
  if (typeof bytes !== 'number') return '–'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const STATUS_CLASSES = {
  Pending: 'secondary',
  Processing: 'info',
  Completed: 'success',
  Failed: 'danger',
  Uploaded: 'secondary',
  Parsed: 'success',
  Accepted: 'success',
  Rejected: 'danger',
  Flagged: 'warning',
  'Potential Duplicate': 'warning',
  'No Significant Overlap': 'success',
}

export function statusClass(status) {
  return `text-bg-${STATUS_CLASSES[status] || 'light'}`
}

export const PIPELINE_STAGE_LABELS = {
  queued: 'Queued',
  parsing: 'Parsing documents',
  preprocessing: 'Preprocessing text',
  keywords: 'Extracting keywords (TF-IDF)',
  entities: 'Recognising skills (NER)',
  embeddings: 'Computing embeddings (SBERT)',
  topics: 'Modelling topics (BERTopic)',
  overlap: 'Checking overlap with NUC core',
  scoring: 'Scoring recommendations',
  saving: 'Saving results',
}

export const SOURCE_CATEGORIES = [
  'Job Market Data',
  'Policy Document',
  'Institutional Document',
  'Academic Literature',
  'NUC Core Reference',
]
