import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { NucDiscipline } from '@/types/api'

import { useDisciplines } from './api'

const NONE = 'none'

/** Choose one of the 17 NUC disciplines, or none (`noneLabel`). */
export function DisciplineSelect({
  id,
  value,
  onChange,
  noneLabel,
  showCounts = false,
  className,
  'aria-invalid': invalid,
}: {
  id: string
  value: NucDiscipline | null
  onChange: (value: NucDiscipline | null) => void
  noneLabel: string
  /** Show how many skills each discipline's list has. */
  showCounts?: boolean
  className?: string
  'aria-invalid'?: boolean
}) {
  const disciplines = useDisciplines()

  return (
    <Select
      value={value ?? NONE}
      onValueChange={(next) => onChange(next === NONE ? null : (next as NucDiscipline))}
    >
      <SelectTrigger id={id} className={className} aria-invalid={invalid}>
        <SelectValue placeholder={disciplines.isPending ? 'Loading…' : undefined} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>
          {noneLabel}
          {showCounts && disciplines.data ? ` (${disciplines.data.general_skills} skills)` : ''}
        </SelectItem>
        {disciplines.data?.disciplines.map((discipline) => (
          <SelectItem key={discipline.value} value={discipline.value}>
            {discipline.name}
            {showCounts ? ` (${discipline.skills} skills)` : ''}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
