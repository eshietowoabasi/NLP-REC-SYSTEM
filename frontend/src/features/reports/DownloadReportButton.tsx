import { useQueryClient } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { useState, type ComponentProps } from 'react'

import { Button } from '@/components/ui/button'
import type { ReportFormat } from '@/types/api'

import { generateAndDownload } from './download'

/** One click: a report with every section (Word unless `format` says PDF), downloaded when ready. */
export function DownloadReportButton({
  sessionId,
  format = 'docx',
  children = 'Download report',
  ...props
}: { sessionId: number; format?: ReportFormat } & Omit<ComponentProps<typeof Button>, 'onClick'>) {
  const queryClient = useQueryClient()
  const [pending, setPending] = useState(false)
  return (
    <Button
      {...props}
      disabled={pending || props.disabled}
      onClick={async () => {
        setPending(true)
        try {
          await generateAndDownload(queryClient, sessionId, { format })
        } finally {
          setPending(false)
        }
      }}
    >
      {pending ? (
        <Loader2 className="animate-spin" aria-hidden="true" />
      ) : (
        <Download aria-hidden="true" />
      )}
      {children}
    </Button>
  )
}
