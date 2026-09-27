import type { SessionStage, SessionStatus } from '@/types/api'

/** Pipeline stages in order, as shown in the stage tracker. */
export const PIPELINE_STAGES: { id: SessionStage; label: string; description: string }[] = [
  {
    id: 'validating',
    label: 'Checking',
    description: 'Checking the documents, the NUC core and the settings',
  },
  { id: 'loading', label: 'Loading', description: 'Collecting the extracts and the NUC core' },
  { id: 'keywords', label: 'Keywords', description: 'Finding the words that stand out' },
  { id: 'skills', label: 'Skills', description: 'Finding skills, tools and certifications' },
  { id: 'embeddings', label: 'Meaning', description: 'Preparing the meaning of each extract' },
  { id: 'themes', label: 'Topics', description: 'Grouping extracts into topics and naming them' },
  { id: 'overlap', label: 'NUC core', description: 'Comparing topics with the NUC core' },
  { id: 'scoring', label: 'Scoring', description: 'Scoring and ranking the topics' },
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
