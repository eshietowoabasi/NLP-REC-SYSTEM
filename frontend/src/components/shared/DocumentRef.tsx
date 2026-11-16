import { Link } from 'react-router'

import { documentMeta, type DocumentRefData } from '@/features/documents/labels'
import { cn } from '@/lib/utils'

/**
 * A document reference (design brief): the title, then a muted line with type · source ·
 * date. File names are never shown.
 */
export function DocumentRef({
  document,
  link = false,
  className,
  titleClassName,
}: {
  document: DocumentRefData
  /** Link the title to the document's page. */
  link?: boolean
  className?: string
  titleClassName?: string
}) {
  const meta = documentMeta(document)
  const title = cn('text-sm font-bold text-ink', titleClassName)
  return (
    <span className={cn('flex min-w-0 flex-col gap-0.5', className)}>
      {link && document.id != null ? (
        <Link to={`/documents/${document.id}`} className={cn(title, 'hover:text-primary')}>
          {document.title}
        </Link>
      ) : (
        <span className={title}>{document.title}</span>
      )}
      {meta && <span className="text-xs text-muted-ink">{meta}</span>}
    </span>
  )
}
