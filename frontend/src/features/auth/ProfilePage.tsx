import { Pencil } from 'lucide-react'
import { Link } from 'react-router'

import { UserAvatar } from '@/components/layout/UserAvatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, formatDateTime } from '@/lib/format'
import { ROLE_DESCRIPTIONS, ROLE_LABELS } from '@/lib/roles'

import { ChangePasswordForm } from './ChangePasswordForm'
import { useAuth } from './useAuth'

const ROLE_BADGES = { admin: 'brand', planner: 'warning', viewer: 'info' } as const

/** Profile (Profile.dc.html): who you are on the left, change password on the right. */
export function ProfilePage() {
  const { user, isAdmin } = useAuth()

  const details: [string, React.ReactNode][] = [
    ['Username', user.username],
    ['Email', user.email],
    ['Last sign-in', formatDateTime(user.last_login_at)],
    ['Member since', formatDate(user.created_at)],
  ]

  return (
    <div className="mx-auto grid max-w-6xl items-start gap-[18px] lg:grid-cols-[460px_minmax(0,1fr)]">
      <section
        aria-label="Your details"
        className="flex flex-col gap-4 rounded-[22px] border border-line bg-white p-[26px]"
      >
        <div className="flex items-center gap-4">
          <UserAvatar name={user.full_name} role={user.role} size={64} />
          <div className="flex min-w-0 flex-col gap-1">
            <h2 className="text-xl font-extrabold break-words text-ink">{user.full_name}</h2>
            <Badge variant={ROLE_BADGES[user.role]}>{ROLE_LABELS[user.role]}</Badge>
          </div>
        </div>
        <p className="text-[13px] leading-normal text-body-soft">{ROLE_DESCRIPTIONS[user.role]}</p>
        <dl className="flex flex-col gap-3 border-t border-divider pt-4 text-sm">
          {details.map(([label, value]) => (
            <div key={label} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
              <dt className="text-body-soft">{label}</dt>
              <dd className="font-bold break-all text-ink">{value}</dd>
            </div>
          ))}
        </dl>
        {isAdmin ? (
          <div className="flex flex-col items-start gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/admin/users?edit=me">
                <Pencil aria-hidden="true" /> Edit name and email
              </Link>
            </Button>
            <p className="text-xs text-muted-ink">
              Your own role cannot be changed, so an active administrator always remains.
            </p>
          </div>
        ) : (
          <p className="text-[13px] leading-normal text-muted-ink">
            To change your name, email or role, contact an administrator.
          </p>
        )}
      </section>
      <Card className="rounded-[22px]">
        <CardHeader>
          <CardTitle className="text-xl">Change password</CardTitle>
          <CardDescription>
            Changing your password signs you out on every other device.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>
    </div>
  )
}
