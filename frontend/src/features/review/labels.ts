import { Check, MessageCircleMore, X } from 'lucide-react'

import type { PlannerDecision, SkillLabel } from '@/types/api'

export const DECISION_LABELS: Record<PlannerDecision, string> = {
  accepted: 'Accepted',
  rejected: 'Rejected',
  flagged: 'Discuss later',
}

/** Imperative forms used on buttons. */
export const DECISION_ACTIONS: Record<PlannerDecision, string> = {
  accepted: 'Accept',
  rejected: 'Reject',
  flagged: 'Discuss later',
}

export const DECISION_ICONS = { accepted: Check, rejected: X, flagged: MessageCircleMore } as const

export const DECISIONS: readonly PlannerDecision[] = ['accepted', 'rejected', 'flagged']

/** The course design form of an accepted recommendation. */
export const designCoursePath = (recommendationId: number) =>
  `/recommendations/${recommendationId}/mapping`

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

/*
 * Scores are computed as decimals from 0 to 1 and shown to planners out of 100. The exact
 * decimals stay available behind "Show calculation" (and in the CSV export).
 */

/** The exact decimal (for "Show calculation"): 0.8492 → "0.85". */
export const formatDecimal = (value: number) => value.toFixed(2)

/** 0.8492 → 85 (whole points out of 100). */
export const toPoints = (value: number) => Math.round(Math.min(Math.max(value, 0), 1) * 100)

/** 0.8492 → "85/100". */
export const formatOutOf100 = (value: number) => `${toPoints(value)}/100`

/** A similarity or threshold as a percentage: 0.576 → "58%". */
export const formatPercent = (value: number) => `${toPoints(value)}%`

/** A weight as "counts for 40%". */
export const formatWeight = (weight: number) => `counts for ${Math.round(weight * 100)}%`

export type ScoreLevel = 'High' | 'Medium' | 'Low'

/** High (70+), Medium (40–69) or Low (below 40), on the rounded points. */
export function scoreLevel(value: number): ScoreLevel {
  const points = toPoints(value)
  return points >= 70 ? 'High' : points >= 40 ? 'Medium' : 'Low'
}

/**
 * Whole-point contributions of the weighted parts that add up exactly to the rounded
 * composite (largest-remainder rounding), so "39 + 17 + 11 = 67" never looks wrong.
 */
export function contributionPoints(contributions: number[], composite: number): number[] {
  const exact = contributions.map((c) => Math.max(c, 0) * 100)
  const floors = exact.map(Math.floor)
  let missing = toPoints(composite) - floors.reduce((a, b) => a + b, 0)
  const order = exact
    .map((value, index) => ({ index, remainder: value - floors[index] }))
    .sort((a, b) => b.remainder - a.remainder)
  const result = [...floors]
  for (const { index } of order) {
    if (missing <= 0) break
    result[index] += 1
    missing -= 1
  }
  return result
}
