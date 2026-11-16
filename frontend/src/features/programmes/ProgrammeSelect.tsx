import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ProgrammeRef } from '@/types/api'

import { programmeName } from './labels'

/** Select value meaning "no programme": a general document, or no programme filter. */
const NO_PROGRAMME = 'none'

interface ProgrammeSelectProps {
  id: string
  programmes: ProgrammeRef[]
  /** A programme id, or null for the "no programme" option. */
  value: number | null
  onChange: (value: number | null) => void
  /** Label of the "no programme" option, e.g. "All programmes (general document)". */
  noneLabel: string
  disabled?: boolean
  className?: string
}

/** Choose one programme, or none (general document / all programmes). */
export function ProgrammeSelect({
  id,
  programmes,
  value,
  onChange,
  noneLabel,
  disabled,
  className,
}: ProgrammeSelectProps) {
  return (
    <Select
      value={value === null ? NO_PROGRAMME : String(value)}
      onValueChange={(next) => onChange(next === NO_PROGRAMME ? null : Number(next))}
      disabled={disabled}
    >
      <SelectTrigger id={id} className={className}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NO_PROGRAMME}>{noneLabel}</SelectItem>
        {programmes.map((programme) => (
          <SelectItem key={programme.id} value={String(programme.id)}>
            {programmeName(programme)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
