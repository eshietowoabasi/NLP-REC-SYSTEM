import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { ApiStatusIndicator } from '@/features/system/ApiStatusIndicator'

import { usePageTitle } from './usePageTitle'

export function TopBar() {
  const title = usePageTitle()

  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" aria-label="Toggle navigation" />
      <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
      <h1 className="truncate text-base font-semibold">{title}</h1>
      <div className="ml-auto flex items-center gap-4">
        <ApiStatusIndicator />
      </div>
    </header>
  )
}
