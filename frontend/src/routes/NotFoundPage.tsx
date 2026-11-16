import { SearchX } from 'lucide-react'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60svh] items-center justify-center">
      <div className="flex max-w-[520px] flex-col items-center gap-[18px] text-center">
        <span className="flex size-24 items-center justify-center rounded-[28px] bg-terracotta-tint">
          <SearchX className="size-11 text-terracotta" strokeWidth={1.6} aria-hidden="true" />
        </span>
        <p className="text-sm font-extrabold tracking-[0.1em] text-primary">404</p>
        <h2 className="page-title">Page not found</h2>
        <p className="text-[15px] leading-relaxed text-body-soft">
          The page you are looking for does not exist or has been moved.
        </p>
        <Button size="lg" asChild>
          <Link to="/">Back to dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
