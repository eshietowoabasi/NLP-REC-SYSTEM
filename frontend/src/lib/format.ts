const dateTime = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
const dateOnly = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' })

/** "24 Sept 2026, 14:05" in the viewer's time zone, or a fallback for null. */
export function formatDateTime(iso: string | null, fallback = '—'): string {
  return iso ? dateTime.format(new Date(iso)) : fallback
}

export function formatDate(iso: string | null, fallback = '—'): string {
  return iso ? dateOnly.format(new Date(iso)) : fallback
}

/** Up to two initials for an avatar: "Ada Lovelace" → "AL". */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts
  return letters.map((part) => part[0]?.toUpperCase() ?? '').join('') || '?'
}
