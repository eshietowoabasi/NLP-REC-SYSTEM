import { useQueryClient } from '@tanstack/react-query'
import { Loader2, UserMinus, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { EmptyState } from '@/components/shared/EmptyState'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useUpdateUser, useUsers } from '@/features/admin/users/api'
import { programmesQueryKey } from '@/features/programmes/api'
import { ROLE_LABELS } from '@/lib/roles'
import type { Programme, User } from '@/types/api'

/** The most people one programme screen lists (the API's page limit). */
const LIMIT = 100

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

/**
 * Planners and viewers who work on a programme, with quick add and remove. Admins see every
 * programme, so they are not listed. Roles and passwords are changed on the Users page.
 */
export function ProgrammePeople({ programme }: { programme: Programme }) {
  const members = useUsers({ programme_id: programme.id, per_page: LIMIT })
  const everyone = useUsers({ is_active: 'true', per_page: LIMIT })
  const update = useUpdateUser()
  const queryClient = useQueryClient()
  const [chosen, setChosen] = useState('')

  if (members.isPending) return <Skeleton className="h-48 w-full rounded-[14px]" />
  if (members.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the people of {programme.name}</AlertTitle>
        <AlertDescription>{members.error.message}</AlertDescription>
      </Alert>
    )
  }

  const people = members.data.items
  const memberIds = new Set(people.map((person) => person.id))
  const candidates = (everyone.data?.items ?? []).filter(
    (person) => person.role !== 'admin' && !memberIds.has(person.id),
  )

  const change = (person: User, add: boolean) => {
    const ids = person.programmes.map((p) => p.id).filter((id) => id !== programme.id)
    update.mutate(
      { id: person.id, changes: { programme_ids: add ? [...ids, programme.id] : ids } },
      {
        onSuccess: () => {
          toast.success(
            add
              ? `${person.full_name} now works on ${programme.name}.`
              : `${person.full_name} no longer works on ${programme.name}.`,
          )
          setChosen('')
          // The readiness card counts the programme's planners.
          void queryClient.invalidateQueries({ queryKey: programmesQueryKey })
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  const toAdd = candidates.find((person) => String(person.id) === chosen)

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section
        aria-labelledby="people-title"
        className="overflow-hidden rounded-[14px] border border-line bg-white"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-4 pb-3">
          <h3 id="people-title" className="card-title">
            People working on {programme.name}
          </h3>
          <span className="num text-xs text-muted-ink">
            {people.length} {people.length === 1 ? 'person' : 'people'}
          </span>
        </div>
        {people.length === 0 ? (
          <EmptyState icon={Users} title="Nobody is assigned yet" className="border-0">
            Add the planners who will review {programme.name}, and any viewers such as the Dean or
            QA. Admins can always reach every programme.
          </EmptyState>
        ) : (
          <ul className="divide-y divide-line border-t border-line">
            {people.map((person) => (
              <li key={person.id} className="flex items-center gap-3 px-5 py-3">
                <span
                  aria-hidden="true"
                  className="flex size-9 shrink-0 items-center justify-center rounded-full bg-sand-deep text-[12px] font-extrabold text-ink"
                >
                  {initials(person.full_name)}
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-sm font-bold text-ink">
                    {person.full_name}
                    {!person.is_active && (
                      <span className="font-normal text-muted-ink"> (deactivated)</span>
                    )}
                  </span>
                  <span className="truncate text-xs text-body-soft">
                    {person.username}
                    {person.programmes.length > 1 &&
                      ` · also ${person.programmes
                        .filter((p) => p.id !== programme.id)
                        .map((p) => p.discipline_code ?? p.name)
                        .join(', ')}`}
                  </span>
                </span>
                <Badge variant={person.role === 'planner' ? 'brand' : 'neutral'}>
                  {ROLE_LABELS[person.role]}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${person.full_name} from ${programme.name}`}
                  disabled={update.isPending}
                  onClick={() => change(person, false)}
                >
                  <UserMinus aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        aria-labelledby="add-person-title"
        className="space-y-3 rounded-[14px] border border-line bg-white px-5 py-4"
      >
        <h3 id="add-person-title" className="card-title">
          Add someone
        </h3>
        {everyone.isPending ? (
          <Skeleton className="h-10 w-full" />
        ) : candidates.length === 0 ? (
          <p className="text-sm text-body-soft">
            Every active planner and viewer already works on {programme.name}.{' '}
            <Link to="/admin/users" className="font-bold text-primary hover:underline">
              Create an account
            </Link>{' '}
            for someone new.
          </p>
        ) : (
          <>
            <div className="grid gap-1.5">
              <Label htmlFor="add-person">Planner or viewer</Label>
              <Select value={chosen} onValueChange={setChosen}>
                <SelectTrigger id="add-person" className="w-full">
                  <SelectValue placeholder="Choose a person" />
                </SelectTrigger>
                <SelectContent>
                  {candidates.map((person) => (
                    <SelectItem key={person.id} value={String(person.id)}>
                      {person.full_name} ({ROLE_LABELS[person.role]})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              className="w-full"
              disabled={!toAdd || update.isPending}
              onClick={() => toAdd && change(toAdd, true)}
            >
              {update.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <UserPlus aria-hidden="true" />
              )}
              Add to {programme.name}
            </Button>
            <p className="text-xs text-body-soft">
              New accounts are created on the{' '}
              <Link to="/admin/users" className="font-bold text-primary hover:underline">
                Users
              </Link>{' '}
              page.
            </p>
          </>
        )}
      </section>
    </div>
  )
}
