import { Check, Flag, X } from 'lucide-react'

import type { PlannerDecision, SkillLabel } from '@/types/api'

export const DECISION_LABELS: Record<PlannerDecision, string> = {
  accepted: 'Accepted',
  rejected: 'Rejected',
  flagged: 'Flagged',
}

/** Imperative forms used on buttons. */
export const DECISION_ACTIONS: Record<PlannerDecision, string> = {
  accepted: 'Accept',
  rejected: 'Reject',
  flagged: 'Flag',
}

export const DECISION_ICONS = { accepted: Check, rejected: X, flagged: Flag } as const

export const DECISIONS: readonly PlannerDecision[] = ['accepted', 'rejected', 'flagged']

export const SKILL_LABELS: Record<SkillLabel, string> = {
  SKILL: 'Skill',
  TOOL: 'Tool',
  CERT: 'Certification',
  LANGUAGE: 'Language',
}

/** The three sub-scores in the order of the composite formula. */
export const SCORE_PARTS = [
  { key: 'ner', field: 'ner_score', label: 'Skill demand' },
  { key: 'topic', field: 'topic_score', label: 'Theme strength' },
  { key: 'novelty', field: 'novelty_score', label: 'Novelty' },
] as const

export const formatScore = (value: number) => value.toFixed(2)
