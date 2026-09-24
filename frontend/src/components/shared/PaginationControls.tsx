import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { Pagination } from '@/types/api'

interface PaginationControlsProps {
  pagination: Pagination
  onPageChange: (page: number) => void
  /** Noun for the total, e.g. "users". */
  itemLabel: string
}

export function PaginationControls({
  pagination,
  onPageChange,
  itemLabel,
}: PaginationControlsProps) {
  const { page, pages, total } = pagination
  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"
    >
      <span>
        {total} {itemLabel} · page {pages === 0 ? 0 : page} of {pages}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft aria-hidden="true" /> Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
        >
          Next <ChevronRight aria-hidden="true" />
        </Button>
      </div>
    </nav>
  )
}
