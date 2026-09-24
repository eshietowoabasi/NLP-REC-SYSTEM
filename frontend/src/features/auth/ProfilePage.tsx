import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, formatDateTime } from '@/lib/format'
import { ROLE_DESCRIPTIONS, ROLE_LABELS } from '@/lib/roles'

import { ChangePasswordForm } from './ChangePasswordForm'
import { useAuth } from './useAuth'

export function ProfilePage() {
  const { user } = useAuth()

  const details: [string, React.ReactNode][] = [
    ['Full name', user.full_name],
    ['Username', user.username],
    ['Email', user.email],
    [
      'Role',
      <Badge key="role" variant="secondary">
        {ROLE_LABELS[user.role]}
      </Badge>,
    ],
    ['Last sign-in', formatDateTime(user.last_login_at)],
    ['Member since', formatDate(user.created_at)],
  ]

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Your details</CardTitle>
          <CardDescription>{ROLE_DESCRIPTIONS[user.role]}</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[10rem_1fr]">
            {details.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-medium break-all">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-muted-foreground">
            To change your name, email or role, contact an administrator.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
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
