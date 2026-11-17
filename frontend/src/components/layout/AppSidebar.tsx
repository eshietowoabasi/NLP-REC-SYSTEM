import { ArrowRight } from 'lucide-react'
import { Link, matchPath, NavLink, useLocation } from 'react-router'

import { Logo, LogoMark } from '@/components/brand/Logo'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { useAuth } from '@/features/auth/useAuth'

import { NAV_SECTIONS, type NavItem } from './navigation'
import { ProgrammeSwitcher } from './ProgrammeSwitcher'

const ITEM_CLASSES =
  'h-10 gap-3 rounded-lg px-3 text-sm font-semibold text-night-text transition-colors hover:bg-night-raised hover:text-white data-[active=true]:bg-night-raised data-[active=true]:font-bold data-[active=true]:text-white data-[active=true]:shadow-[inset_2px_0_0_var(--color-ember)] [&>svg]:size-[18px] group-data-[collapsible=icon]:size-10! group-data-[collapsible=icon]:p-2.5!'

function SidebarNavLink({ item }: { item: NavItem }) {
  const { pathname } = useLocation()
  const end = item.to === '/'
  const isActive = [item.to, ...(item.alsoActive ?? [])].some(
    (path) => matchPath({ path, end }, pathname) !== null,
  )
  return (
    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label} className={ITEM_CLASSES}>
      <NavLink to={item.to} end={end}>
        <item.icon aria-hidden="true" strokeWidth={1.8} />
        <span>{item.label}</span>
      </NavLink>
    </SidebarMenuButton>
  )
}

/** Dark SkillBridge sidebar: logo, programme switcher, Workspace, Admin (admins) and help. */
export function AppSidebar() {
  const { user } = useAuth()
  const sections = NAV_SECTIONS.filter(
    (section) => !section.roles || section.roles.includes(user.role),
  )

  return (
    <Sidebar collapsible="icon" aria-label="Main navigation" className="border-r-0">
      <SidebarHeader className="px-4 pt-[22px] pb-1 group-data-[collapsible=icon]:px-2">
        <Link
          to="/"
          aria-label="SkillBridge home"
          className="flex items-center rounded-xl px-2 py-1 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0 focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none"
        >
          <Logo
            size={38}
            tone="dark"
            subtitle="University of Uyo"
            className="group-data-[collapsible=icon]:hidden"
          />
          <LogoMark
            size={30}
            tone="dark"
            title=""
            className="hidden group-data-[collapsible=icon]:block"
          />
        </Link>
        <div className="mt-4 group-data-[collapsible=icon]:mt-2">
          <ProgrammeSwitcher />
        </div>
      </SidebarHeader>
      <SidebarContent className="gap-[18px] px-2 pt-3">
        {sections.map((section) => (
          <SidebarGroup key={section.id} className="py-0">
            <SidebarGroupLabel className="h-auto px-3 pb-1.5 text-[10.5px] font-extrabold tracking-[0.1em] text-night-muted uppercase">
              {section.label}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu className="gap-1">
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.to}>
                    {item.available ? (
                      <SidebarNavLink item={item} />
                    ) : (
                      <SidebarMenuButton
                        aria-disabled="true"
                        disabled
                        tooltip={`${item.label} (not yet available)`}
                        className={`${ITEM_CLASSES} opacity-50`}
                      >
                        <item.icon aria-hidden="true" />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    )}
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className="px-4 pb-[22px] group-data-[collapsible=icon]:hidden">
        <section
          aria-label="New here?"
          className="flex flex-col gap-1.5 rounded-xl border border-night-line bg-night-raised p-3.5 text-night-text"
        >
          <p className="text-[13px] font-extrabold text-white">New here?</p>
          <p className="text-xs leading-normal">
            Gather evidence, review topics, design courses, then download your report.
          </p>
          <Link
            to="/?help=1"
            className="inline-flex items-center gap-1 text-xs font-bold text-ember-soft hover:underline"
          >
            See how it works <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </section>
      </SidebarFooter>
    </Sidebar>
  )
}
