import { KeyRound, MoreHorizontal, Pencil, Search, UserCheck, UserPlus, UserX } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { PaginationControls } from '@/components/shared/PaginationControls'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { formatDateTime } from '@/lib/format'
import { ROLE_LABELS, ROLES } from '@/lib/roles'
import type { User, UserListParams, UserRole } from '@/types/api'

import { useUpdateUser, useUsers } from './api'
import { ResetPasswordDialog } from './ResetPasswordDialog'
import { UserFormDialog } from './UserFormDialog'

const PER_PAGE = 20
type RoleFilter = UserRole | 'all'
type StatusFilter = 'all' | 'true' | 'false'

export function UsersPage() {
  const { user: me } = useAuth()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<RoleFilter>('all')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebouncedValue(search.trim())

  const params: UserListParams = {
    page,
    per_page: PER_PAGE,
    search: debouncedSearch || undefined,
    role: role === 'all' ? undefined : role,
    is_active: status === 'all' ? undefined : status,
  }
  const users = useUsers(params)

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [resetting, setResetting] = useState<User | null>(null)
  const [toggling, setToggling] = useState<User | null>(null)

  const filtersActive = debouncedSearch !== '' || role !== 'all' || status !== 'all'
  const resetToFirstPage =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value)
      setPage(1)
    }

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Users</h2>
          <p className="text-sm text-muted-foreground">
            Create accounts, change roles and deactivate users. Users are never deleted.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <UserPlus aria-hidden="true" /> Add user
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3" role="search">
        <div className="grid min-w-56 flex-1 gap-1.5">
          <Label htmlFor="user-search">Search</Label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="user-search"
              className="pl-8"
              placeholder="Name, username or email"
              value={search}
              onChange={(event) => resetToFirstPage(setSearch)(event.target.value)}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="role-filter">Role</Label>
          <Select value={role} onValueChange={(v) => resetToFirstPage(setRole)(v as RoleFilter)}>
            <SelectTrigger id="role-filter" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All roles</SelectItem>
              {ROLES.map((value) => (
                <SelectItem key={value} value={value}>
                  {ROLE_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="status-filter">Status</Label>
          <Select
            value={status}
            onValueChange={(v) => resetToFirstPage(setStatus)(v as StatusFilter)}
          >
            <SelectTrigger id="status-filter" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="true">Active</SelectItem>
              <SelectItem value="false">Deactivated</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {users.isError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load users</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{users.error.message}</p>
            <Button variant="outline" size="sm" onClick={() => void users.refetch()}>
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last sign-in</TableHead>
                <TableHead className="w-12">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.isPending ? (
                Array.from({ length: 4 }, (_, index) => (
                  <TableRow key={index} aria-hidden="true">
                    <TableCell colSpan={6}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : users.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    {filtersActive ? 'No users match these filters.' : 'No users yet.'}
                  </TableCell>
                </TableRow>
              ) : (
                users.data.items.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    isSelf={user.id === me.id}
                    onEdit={() => setEditing(user)}
                    onResetPassword={() => setResetting(user)}
                    onToggleActive={() => setToggling(user)}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {users.data && users.data.pagination.pages > 1 && (
        <PaginationControls
          pagination={users.data.pagination}
          onPageChange={setPage}
          itemLabel="users"
        />
      )}

      <UserFormDialog open={creating} onOpenChange={setCreating} />
      <UserFormDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        user={editing ?? undefined}
        isSelf={editing?.id === me.id}
      />
      <ResetPasswordDialog user={resetting} onOpenChange={(open) => !open && setResetting(null)} />
      <ToggleActiveDialog user={toggling} onOpenChange={(open) => !open && setToggling(null)} />
    </div>
  )
}

interface UserRowProps {
  user: User
  isSelf: boolean
  onEdit: () => void
  onResetPassword: () => void
  onToggleActive: () => void
}

function UserRow({ user, isSelf, onEdit, onResetPassword, onToggleActive }: UserRowProps) {
  return (
    <TableRow className={user.is_active ? undefined : 'text-muted-foreground'}>
      <TableCell>
        <div className="font-medium text-foreground">
          {user.full_name}
          {isSelf && <span className="ml-2 text-xs text-muted-foreground">(you)</span>}
        </div>
        <div className="text-xs text-muted-foreground">{user.username}</div>
      </TableCell>
      <TableCell className="break-all">{user.email}</TableCell>
      <TableCell>
        <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
          {ROLE_LABELS[user.role]}
        </Badge>
      </TableCell>
      <TableCell>
        {user.is_active ? (
          <Badge variant="outline" className="text-emerald-700 dark:text-emerald-400">
            Active
          </Badge>
        ) : (
          <Badge variant="outline">Deactivated</Badge>
        )}
      </TableCell>
      <TableCell className="whitespace-nowrap">
        {formatDateTime(user.last_login_at, 'Never')}
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label={`Actions for ${user.username}`}>
              <MoreHorizontal aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onEdit}>
              <Pencil aria-hidden="true" /> Edit details
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onResetPassword}>
              <KeyRound aria-hidden="true" /> Reset password
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={onToggleActive}
              disabled={isSelf}
              variant={user.is_active ? 'destructive' : 'default'}
            >
              {user.is_active ? (
                <>
                  <UserX aria-hidden="true" /> Deactivate
                </>
              ) : (
                <>
                  <UserCheck aria-hidden="true" /> Reactivate
                </>
              )}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  )
}

function ToggleActiveDialog({
  user,
  onOpenChange,
}: {
  user: User | null
  onOpenChange: (open: boolean) => void
}) {
  const updateUser = useUpdateUser()
  const deactivating = user?.is_active ?? false

  const confirm = () => {
    if (!user) return
    updateUser.mutate(
      { id: user.id, changes: { is_active: !user.is_active } },
      {
        onSuccess: () => {
          toast.success(
            deactivating ? `${user.username} deactivated.` : `${user.username} reactivated.`,
          )
          onOpenChange(false)
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <AlertDialog open={user !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {deactivating ? 'Deactivate' : 'Reactivate'} {user?.full_name}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            {deactivating
              ? 'They will be signed out immediately and will not be able to sign in. Their past work and audit history are kept.'
              : 'They will be able to sign in again with their existing password.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(event) => {
              event.preventDefault()
              confirm()
            }}
            disabled={updateUser.isPending}
            variant={deactivating ? 'destructive' : 'default'}
          >
            {deactivating ? 'Deactivate' : 'Reactivate'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
