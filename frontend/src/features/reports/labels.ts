import type { ReportFormat, ReportSection, ReportStatus } from '@/types/api'

/** Report sections in report order, with the description shown in the generate dialog. */
export const REPORT_SECTIONS: { id: ReportSection; label: string; hint: string }[] = [
  {
    id: 'corpus_summary',
    label: 'Corpus summary',
    hint: 'Documents analysed, by category, with page, word and passage counts',
  },
  {
    id: 'nlp_findings',
    label: 'NLP findings',
    hint: 'Top TF-IDF terms, skills in demand and the themes discovered',
  },
  {
    id: 'overlap',
    label: 'Overlap results',
    hint: 'Similarity of each theme to the NUC core, with potential duplicates',
  },
  {
    id: 'recommendations',
    label: 'Recommendations',
    hint: 'Ranked topics with the score formula and descriptions',
  },
  {
    id: 'decisions',
    label: 'Decisions',
    hint: 'Accepted, rejected and flagged topics with notes',
  },
  {
    id: 'proposed_courses',
    label: 'Proposed courses',
    hint: 'Mapped courses, learning outcomes and credit units against the allowance',
  },
]

export const FORMAT_LABELS: Record<ReportFormat, string> = { pdf: 'PDF', docx: 'Word (DOCX)' }

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  queued: 'Queued',
  processing: 'Generating',
  completed: 'Ready',
  failed: 'Failed',
}
