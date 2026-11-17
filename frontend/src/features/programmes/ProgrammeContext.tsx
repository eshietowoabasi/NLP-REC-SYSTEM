import { useCallback, useMemo, useState, type ReactNode } from 'react'

import { useAuth } from '@/features/auth/useAuth'
import type { Programme } from '@/types/api'

import { useProgrammes } from './api'
import { ProgrammeContext, type CurrentProgramme } from './useCurrentProgramme'

function storageKey(userId: number) {
  return `skillbridge.programme.${userId}`
}

function readStored(userId: number): number | null {
  try {
    const value = window.localStorage.getItem(storageKey(userId))
    return value ? Number(value) : null
  } catch {
    return null
  }
}

/**
 * The programme the whole workspace follows (Home, reviews, library, uploads, job collection).
 * Chosen once in the sidebar and remembered per user in this browser; it falls back to the
 * user's lowest-numbered programme (for admins the default programme, Computer Science).
 */
export function ProgrammeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const query = useProgrammes()
  const [chosenId, setChosenId] = useState<number | null>(() => readStored(user.id))

  const setProgrammeId = useCallback(
    (id: number) => {
      setChosenId(id)
      try {
        window.localStorage.setItem(storageKey(user.id), String(id))
      } catch {
        // Private windows may block storage; the choice then lasts for this visit only.
      }
    },
    [user.id],
  )

  const value = useMemo<CurrentProgramme>(() => {
    const programmes = query.data ?? []
    const fallback = programmes.reduce<Programme | undefined>(
      (lowest, programme) =>
        lowest === undefined || programme.id < lowest.id ? programme : lowest,
      undefined,
    )
    return {
      programmes,
      programme: programmes.find((programme) => programme.id === chosenId) ?? fallback,
      isLoading: query.isPending,
      setProgrammeId,
    }
  }, [query.data, query.isPending, chosenId, setProgrammeId])

  return <ProgrammeContext value={value}>{children}</ProgrammeContext>
}
