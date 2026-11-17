import { createContext, use } from 'react'

import type { Programme } from '@/types/api'

export interface CurrentProgramme {
  /** The programme chosen in the sidebar; undefined while loading or if the user has none. */
  programme: Programme | undefined
  /** The programmes the user may work on (admins: all active ones). */
  programmes: Programme[]
  isLoading: boolean
  setProgrammeId: (id: number) => void
}

export const ProgrammeContext = createContext<CurrentProgramme | null>(null)

/** The programme chosen in the sidebar; use inside <ProgrammeProvider> (the app shell). */
export function useCurrentProgramme(): CurrentProgramme {
  const value = use(ProgrammeContext)
  if (!value) throw new Error('useCurrentProgramme must be used inside <ProgrammeProvider>')
  return value
}
