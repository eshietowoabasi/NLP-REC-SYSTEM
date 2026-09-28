import { Link } from 'react-router'

import { Button } from '@/components/ui/button'

/** The locked keystone arch from NoAccess.dc.html. */
function LockedArch() {
  return (
    <svg width="180" height="140" viewBox="0 0 180 140" fill="none" aria-hidden="true">
      <rect x="20" y="30" width="140" height="96" rx="20" fill="#F8E6DC" />
      <path
        d="M50 108A40 40 0 0 1 130 108"
        stroke="#A8431E"
        strokeWidth="16"
        strokeDasharray="20 4"
      />
      <path d="M36 114H144" stroke="#231A14" strokeWidth="6" strokeLinecap="round" />
      <rect x="72" y="18" width="36" height="30" rx="8" fill="#F2B84B" />
      <path
        d="M80 18v-4a10 10 0 0 1 20 0v4"
        stroke="#231A14"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <circle cx="90" cy="33" r="4" fill="#231A14" />
    </svg>
  )
}

/** Shown for any route the user's role may not open (NoAccess.dc.html). */
export function ForbiddenPage() {
  return (
    <div className="flex min-h-[60svh] items-center justify-center">
      <div className="flex max-w-[520px] flex-col items-center gap-[18px] text-center">
        <LockedArch />
        <p className="text-sm font-extrabold tracking-[0.1em] text-primary">403</p>
        <h2 className="page-title">Access denied</h2>
        <p className="text-[15px] leading-relaxed text-body-soft">
          Your role does not allow access to this page. Ask an administrator if you need it.
        </p>
        <Button size="lg" asChild>
          <Link to="/">Back to dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
