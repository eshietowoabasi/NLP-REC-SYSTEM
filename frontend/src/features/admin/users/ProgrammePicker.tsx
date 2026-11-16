import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { useProgrammes } from '@/features/programmes/api'
import { programmeName } from '@/features/programmes/labels'

/** Tick the programmes a planner or viewer works on. */
export function ProgrammePicker({
  id,
  value,
  onChange,
}: {
  id: string
  value: number[]
  onChange: (ids: number[]) => void
}) {
  const programmes = useProgrammes()

  if (programmes.isPending) return <Skeleton className="h-24 w-full" />
  if (programmes.isError) {
    return <p className="text-sm text-destructive">Could not load programmes.</p>
  }
  if (programmes.data.length === 0) {
    return <p className="text-sm text-muted-foreground">No programmes yet. Add one first.</p>
  }

  return (
    <div
      id={id}
      role="group"
      className="grid max-h-56 gap-1 overflow-y-auto rounded-xl border border-input p-2"
    >
      {programmes.data.map((programme) => {
        const checked = value.includes(programme.id)
        const inputId = `${id}-${programme.id}`
        return (
          <label
            key={programme.id}
            htmlFor={inputId}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm hover:bg-sand"
          >
            <Checkbox
              id={inputId}
              checked={checked}
              onCheckedChange={(next) =>
                onChange(
                  next === true
                    ? [...value, programme.id]
                    : value.filter((programmeId) => programmeId !== programme.id),
                )
              }
            />
            {programmeName(programme)}
          </label>
        )
      })}
    </div>
  )
}
