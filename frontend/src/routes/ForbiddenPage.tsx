import { ShieldAlert } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'

export function ForbiddenPage() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
      <ShieldAlert className="size-12 text-muted-foreground" aria-hidden="true" />
      <p className="text-5xl font-bold text-muted-foreground">403</p>
      <h2 className="text-xl font-semibold">Access denied</h2>
      <p className="text-sm text-muted-foreground">
        Your role does not allow access to this page. Ask an administrator if you need it.
      </p>
      <Button asChild>
        <Link to="/">Back to dashboard</Link>
      </Button>
    </div>
  )
}
