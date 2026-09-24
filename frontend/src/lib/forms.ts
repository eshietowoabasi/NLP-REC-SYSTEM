import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { ApiError } from '@/lib/api'
import type { FieldErrorDetails } from '@/types/api'

/**
 * Copy per-field errors from a 422/409 API error onto a React Hook Form.
 * Returns the message for errors that do not belong to a known field (to show in an alert),
 * or null when every error was attached to a field.
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly Path<T>[],
): string | null {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.'
  const fields = (error.details as FieldErrorDetails).fields ?? {}
  let unmatched = false
  let matched = false
  for (const [field, messages] of Object.entries(fields)) {
    if ((knownFields as readonly string[]).includes(field)) {
      setError(field as Path<T>, { type: 'server', message: messages.join(' ') })
      matched = true
    } else {
      unmatched = true
    }
  }
  return matched && !unmatched ? null : error.message
}
