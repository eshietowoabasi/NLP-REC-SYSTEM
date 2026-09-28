import { Outlet } from 'react-router'

import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'

import { AppSidebar } from './AppSidebar'
import { TopBar } from './TopBar'

/** Authenticated layout: sidebar navigation, top bar and the routed page. */
export function AppShell() {
  return (
    <SidebarProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-xl focus:bg-white focus:px-4 focus:py-2.5 focus:font-bold focus:text-ink focus:shadow-selected"
      >
        Skip to main content
      </a>
      <AppSidebar />
      <SidebarInset className="min-w-0 bg-sand">
        <TopBar />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 px-4 py-6 focus:outline-none md:px-10 md:py-7"
        >
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
