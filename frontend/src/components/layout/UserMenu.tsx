import { ChevronDown, LogOut, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
import { initials } from '@/lib/format'
import { ROLE_LABELS } from '@/lib/roles'

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
    <div className="flex items-center gap-2">
      <Badge variant="secondary" className="hidden md:inline-flex">
        {ROLE_LABELS[user.role]}
      </Badge>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-9 gap-2 px-2" aria-label="Account menu">
            <Avatar className="size-7">
              <AvatarFallback className="text-xs">{initials(user.full_name)}</AvatarFallback>
            </Avatar>
            <span className="hidden max-w-40 truncate text-sm font-medium sm:inline">
              {user.full_name}
            </span>
            <ChevronDown className="size-4 text-muted-foreground" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="font-normal">
            <div className="truncate font-medium">{user.full_name}</div>
            <div className="truncate text-xs text-muted-foreground">{user.email}</div>
            <div className="mt-1 text-xs text-muted-foreground md:hidden">
              {ROLE_LABELS[user.role]}
            </div>
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
    </div>
  )
}
