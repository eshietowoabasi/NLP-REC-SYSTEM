import { SidebarTrigger } from '@/components/ui/sidebar'
import { ApiStatusIndicator } from '@/features/system/ApiStatusIndicator'

import { usePageHeading } from './usePageTitle'
import { UserMenu } from './UserMenu'

/** SkillBridge top bar (TopBar.dc.html): breadcrumb and page title, then the signed-in user. */
export function TopBar() {
  const { title, crumb } = usePageHeading()

  return (
    <header className="sticky top-0 z-10 flex h-[72px] shrink-0 items-center gap-3 border-b border-line bg-white px-4 md:px-10">
      <SidebarTrigger
        className="-ml-1 size-10 rounded-xl border border-line text-body hover:bg-sand md:hidden"
        aria-label="Toggle navigation"
      />
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate text-xs text-muted-ink">{crumb}</span>
        <h1 className="truncate text-[17px] leading-tight font-extrabold tracking-[-0.01em] text-ink">
          {title}
        </h1>
      </div>
      <div className="ml-auto flex items-center gap-3.5">
        <ApiStatusIndicator />
        <UserMenu />
      </div>
    </header>
  )
}
