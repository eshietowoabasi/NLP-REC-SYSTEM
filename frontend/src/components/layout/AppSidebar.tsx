import { GraduationCap } from 'lucide-react'
import { NavLink, useMatch } from 'react-router'

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

import { NAV_SECTIONS, type NavItem } from './navigation'

function SidebarNavLink({ item }: { item: NavItem }) {
  const end = item.to === '/'
  const isActive = useMatch({ path: item.to, end }) !== null
  return (
    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
      <NavLink to={item.to} end={end}>
        <item.icon aria-hidden="true" />
        <span>{item.label}</span>
      </NavLink>
    </SidebarMenuButton>
  )
}

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon" aria-label="Main navigation">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <GraduationCap className="size-4" aria-hidden="true" />
          </div>
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">NLP-RS</span>
            <span className="text-xs text-muted-foreground">Curriculum recommendations</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {NAV_SECTIONS.map((section) => (
          <SidebarGroup key={section.id}>
            <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.to}>
                    {item.available ? (
                      <SidebarNavLink item={item} />
                    ) : (
                      <SidebarMenuButton
                        aria-disabled="true"
                        disabled
                        tooltip={`${item.label} (not yet available)`}
                        className="opacity-50"
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
    </Sidebar>
  )
}
