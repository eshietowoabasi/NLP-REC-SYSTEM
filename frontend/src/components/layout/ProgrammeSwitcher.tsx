import { ChevronsUpDown, Settings2 } from 'lucide-react'
import { Link } from 'react-router'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/useAuth'
import { useProgrammesReadiness } from '@/features/programmes/api'
import { useCurrentProgramme } from '@/features/programmes/useCurrentProgramme'
import { cn } from '@/lib/utils'

function codeOf(name: string, code: string | null) {
  return code ?? name.slice(0, 3).toUpperCase()
}

/** Sidebar control: the programme the whole workspace follows. */
export function ProgrammeSwitcher() {
  const { isAdmin } = useAuth()
  const { programme, programmes, isLoading, setProgrammeId } = useCurrentProgramme()
  const readiness = useProgrammesReadiness()
  const isReady = (id: number) => readiness.data?.find((r) => r.programme_id === id)?.ready

  if (isLoading) return <Skeleton className="h-[58px] w-full bg-night-raised" />

  if (!programme) {
    return (
      <p className="rounded-xl border border-night-line bg-night-raised px-3 py-2.5 text-xs leading-relaxed text-night-text group-data-[collapsible=icon]:hidden">
        You have no programmes yet. Ask an admin to add you to one.
      </p>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Programme: ${programme.name}. Change programme`}
        className="flex w-full items-center gap-2.5 rounded-xl border border-night-line bg-night-raised px-3 py-2.5 text-left text-white transition-colors group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:border-0 group-data-[collapsible=icon]:bg-transparent group-data-[collapsible=icon]:p-1 hover:bg-night-hover focus-visible:ring-3 focus-visible:ring-ember/50 focus-visible:outline-none"
      >
        <span className="shrink-0 rounded-md bg-terracotta px-1.5 py-1 num text-[11px] font-semibold">
          {codeOf(programme.name, programme.discipline_code)}
        </span>
        <span className="flex min-w-0 flex-1 flex-col group-data-[collapsible=icon]:hidden">
          <span className="text-[10.5px] font-bold tracking-[0.06em] text-night-muted">
            PROGRAMME
          </span>
          <span className="truncate text-sm font-bold">{programme.name}</span>
        </span>
        <ChevronsUpDown
          className="size-4 shrink-0 text-night-muted group-data-[collapsible=icon]:hidden"
          aria-hidden="true"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        sideOffset={8}
        className="w-72 border-night-line bg-[#241b16] p-1.5 text-white"
      >
        <DropdownMenuLabel className="text-[10.5px] font-extrabold tracking-[0.08em] text-night-muted">
          {isAdmin ? 'ALL PROGRAMMES' : 'YOUR PROGRAMMES'}
        </DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={String(programme.id)}
          onValueChange={(value) => setProgrammeId(Number(value))}
        >
          {programmes.map((option) => {
            const ready = isReady(option.id)
            return (
              <DropdownMenuRadioItem
                key={option.id}
                value={String(option.id)}
                className="gap-2.5 rounded-lg py-2 pr-8 text-white focus:bg-night-hover focus:text-white [&_svg]:text-ember-soft"
              >
                <span className="rounded bg-night-hover px-1.5 py-0.5 num text-[10.5px] text-ember-soft">
                  {codeOf(option.name, option.discipline_code)}
                </span>
                <span className="flex-1 truncate text-[13.5px] font-semibold">{option.name}</span>
                {ready !== undefined && (
                  <span
                    className={cn('size-2 rounded-full', ready ? 'bg-emerald-400' : 'bg-amber')}
                    role="img"
                    aria-label={ready ? 'Ready' : 'Needs setting up'}
                  />
                )}
              </DropdownMenuRadioItem>
            )
          })}
        </DropdownMenuRadioGroup>
        {isAdmin && (
          <>
            <DropdownMenuSeparator className="bg-night-line" />
            <DropdownMenuItem asChild className="text-ember-soft focus:bg-night-hover">
              <Link to="/admin/benchmarks">
                <Settings2 aria-hidden="true" /> Manage programmes
              </Link>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
