import type { ReportFormat, ReportSection, ReportStatus } from '@/types/api'

/** Report sections in report order, with the description shown in the generate dialog. */
export const REPORT_SECTIONS: { id: ReportSection; label: string; hint: string }[] = [
  {
    id: 'corpus_summary',
    label: 'Documents analysed',
    hint: 'Every document with its type, source, pages, words and extracts',
  },
  {
    id: 'nlp_findings',
    label: 'What the documents talk about',
    hint: 'Words that stand out, skills employers ask for, and the topics found',
  },
  {
    id: 'overlap',
    label: 'Comparison with the NUC core',
    hint: 'How similar each topic is to the NUC core, and which may already be in it',
  },
  {
    id: 'recommendations',
    label: 'Recommended topics',
    hint: 'Topics in order, with their scores and why they are recommended',
  },
  {
    id: 'decisions',
    label: 'Decisions',
    hint: 'Accepted and rejected topics, and those to discuss later, with notes',
  },
  {
    id: 'proposed_courses',
    label: 'Proposed courses',
    hint: 'Designed courses, learning outcomes and credit units against the allowance',
  },
]

export const FORMAT_LABELS: Record<ReportFormat, string> = { pdf: 'PDF', docx: 'Word (DOCX)' }

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  queued: 'Queued',
  processing: 'Generating',
  completed: 'Ready',
  failed: 'Failed',
}
