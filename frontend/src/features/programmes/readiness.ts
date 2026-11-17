import type { ProgrammeReadiness } from '@/types/api'

/** Tabs of the admin Programmes page, used to link a missing item to where it is fixed. */
export type ProgrammeTab = 'overview' | 'core' | 'jobs' | 'people'

export interface ReadinessCheck {
  key: string
  label: string
  ok: (r: ProgrammeReadiness) => boolean
  detail: (r: ProgrammeReadiness) => string
  /** Who fixes it and how, in plain words. */
  fix: string
  /** The Programmes tab where an admin fixes it. */
  tab: ProgrammeTab
}

/** What a programme needs before a useful review (the API's `ready` combines the same items). */
export const READINESS_CHECKS: ReadinessCheck[] = [
  {
    key: 'core',
    label: 'NUC core',
    ok: (r) => r.nuc_core !== null,
    detail: (r) => r.nuc_core?.version_label ?? 'Not uploaded yet',
    fix: 'An admin uploads the CCMAS document.',
    tab: 'core',
  },
  {
    key: 'skills',
    label: 'Skills list',
    ok: (r) => r.discipline !== null,
    detail: (r) => (r.discipline ? r.discipline.name : 'Discipline not chosen'),
    fix: 'An admin chooses the NUC discipline.',
    tab: 'overview',
  },
  {
    key: 'jobs',
    label: 'Job collection',
    ok: (r) => r.job_search.ready,
    detail: (r) =>
      r.job_search.ready ? r.job_search.search_terms.slice(0, 3).join(', ') : 'Not set up',
    fix: 'An admin adds the job titles to look for.',
    tab: 'jobs',
  },
  {
    key: 'documents',
    label: 'Documents',
    ok: (r) => r.documents_ready >= 5,
    detail: (r) => `${r.documents_ready} ready to analyse`,
    fix: 'Collect adverts or upload at least 5 documents.',
    tab: 'jobs',
  },
]

export function readyCount(r: ProgrammeReadiness) {
  return READINESS_CHECKS.filter((check) => check.ok(r)).length
}
