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
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow"
      >
        Skip to main content
      </a>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <TopBar />
        <main id="main-content" tabIndex={-1} className="flex-1 p-4 focus:outline-none md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
