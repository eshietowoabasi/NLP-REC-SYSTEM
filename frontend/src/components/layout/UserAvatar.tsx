import { initials } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { UserRole } from '@/types/api'

/* Avatar colours per role, as in the Users mockup (admin ink, planner amber, viewer teal). */
const ROLE_AVATAR: Record<UserRole, string> = {
  admin: 'bg-ink text-white',
  planner: 'bg-amber text-[#4a2c00]',
  viewer: 'bg-teal-tint text-teal-ink',
}

/** A round initials avatar; the role only chooses its colour. */
export function UserAvatar({
  name,
  role,
  size = 40,
  className,
}: {
  name: string
  role: UserRole
  size?: number
  className?: string
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full font-extrabold',
        ROLE_AVATAR[role],
        className,
      )}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.35) }}
    >
      {initials(name)}
    </span>
  )
}
