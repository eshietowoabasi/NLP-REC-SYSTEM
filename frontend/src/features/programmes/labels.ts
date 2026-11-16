import type { ProgrammeRef } from '@/types/api'

/** "Nursing Science (NSC)", or just the name when there is no code. */
export function programmeName(programme: ProgrammeRef) {
  return programme.discipline_code
    ? `${programme.name} (${programme.discipline_code})`
    : programme.name
}
