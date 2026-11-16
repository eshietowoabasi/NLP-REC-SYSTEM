import { ChevronDown, LogOut, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useLogout } from '@/features/auth/api'
import { useAuth } from '@/features/auth/useAuth'
import { ROLE_LABELS } from '@/lib/roles'

import { UserAvatar } from './UserAvatar'

/** The user chip of the top bar: initials, name and role, opening Profile / Log out. */
export function UserMenu() {
  const { user } = useAuth()
  const logout = useLogout()
  const navigate = useNavigate()

  const signOut = () => {
    logout.mutate(undefined, {
      onSettled: () => navigate('/login', { replace: true }),
      onError: () => toast.error('Could not reach the server; you have been signed out here.'),
    })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Account menu"
          className="flex cursor-pointer items-center gap-2.5 rounded-xl px-1.5 py-1 text-left hover:bg-sand focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none aria-expanded:bg-sand"
        >
          <UserAvatar name={user.full_name} role={user.role} />
          <span className="hidden min-w-0 flex-col sm:flex">
            <span className="max-w-44 truncate text-sm font-bold text-ink">{user.full_name}</span>
            <span className="text-xs text-muted-ink">{ROLE_LABELS[user.role]}</span>
          </span>
          <ChevronDown className="size-4 text-muted-ink" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal">
          <div className="truncate font-bold text-ink">{user.full_name}</div>
          <div className="truncate text-xs text-muted-ink">{user.email}</div>
          <div className="mt-1 text-xs text-muted-ink sm:hidden">{ROLE_LABELS[user.role]}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/profile">
            <UserRound aria-hidden="true" /> Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={signOut} disabled={logout.isPending}>
          <LogOut aria-hidden="true" /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
