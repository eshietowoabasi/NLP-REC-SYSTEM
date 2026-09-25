import type { SessionStage, SessionStatus } from '@/types/api'

/** Pipeline stages in order, as shown in the stage tracker. */
export const PIPELINE_STAGES: { id: SessionStage; label: string; description: string }[] = [
  {
    id: 'validating',
    label: 'Validating',
    description: 'Checking documents, NUC core and weights',
  },
  { id: 'loading', label: 'Loading', description: 'Collecting passages and the NUC core' },
  { id: 'keywords', label: 'Keywords', description: 'TF-IDF keywords overall and per category' },
  { id: 'skills', label: 'Skills', description: 'Skills, tools and certifications (NER)' },
  { id: 'embeddings', label: 'Embeddings', description: 'Reusing stored SBERT embeddings' },
  { id: 'themes', label: 'Themes', description: 'Discovering themes with BERTopic' },
  { id: 'overlap', label: 'Overlap', description: 'Comparing themes with the NUC core' },
  { id: 'scoring', label: 'Scoring', description: 'Scoring and ranking recommendations' },
]

export type StageState = 'done' | 'current' | 'failed' | 'waiting'

/** State of each stage given the session's status and current stage. */
export function stageStates(
  status: SessionStatus,
  currentStage: SessionStage | null,
): Record<SessionStage, StageState> {
  const states = {} as Record<SessionStage, StageState>
  const currentIndex = PIPELINE_STAGES.findIndex((stage) => stage.id === currentStage)
  PIPELINE_STAGES.forEach((stage, index) => {
    if (status === 'completed') states[stage.id] = 'done'
    else if (status === 'pending' || currentIndex < 0) states[stage.id] = 'waiting'
    else if (index < currentIndex) states[stage.id] = 'done'
    else if (index === currentIndex) states[stage.id] = status === 'failed' ? 'failed' : 'current'
    else states[stage.id] = 'waiting'
  })
  return states
}

export const STATUS_LABELS: Record<SessionStatus, string> = {
  pending: 'Not run',
  processing: 'Running',
  completed: 'Completed',
  failed: 'Failed',
}
