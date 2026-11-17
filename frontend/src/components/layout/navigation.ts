import {
  BriefcaseBusiness,
  FileText,
  GraduationCap,
  History,
  House,
  Library,
  ListChecks,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'

import type { UserRole } from '@/types/api'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** False until the screen exists; the sidebar shows the item disabled. */
  available: boolean
  /** Other paths that belong to this item (e.g. a topic's page lives under Analyses). */
  alsoActive?: string[]
}

export interface NavSection {
  id: 'main' | 'admin'
  label: string
  /** Roles that see this section; omitted means everyone. Cosmetic only: the API enforces. */
  roles?: UserRole[]
  items: NavItem[]
}

/**
 * Sidebar structure (UX redesign): Home, Reviews, Library and Reports for everyone; admin
 * setup underneath. Every page follows the programme chosen at the top of the sidebar.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'main',
    label: 'Workspace',
    items: [
      { label: 'Home', to: '/', icon: House, available: true },
      {
        label: 'Reviews',
        to: '/sessions',
        icon: ListChecks,
        available: true,
        alsoActive: ['/recommendations/*'],
      },
      { label: 'Library', to: '/documents', icon: Library, available: true },
      { label: 'Reports', to: '/reports', icon: FileText, available: true },
    ],
  },
  {
    id: 'admin',
    label: 'Admin',
    roles: ['admin'],
    items: [
      { label: 'Programmes', to: '/admin/benchmarks', icon: GraduationCap, available: true },
      {
        label: 'Job collection',
        to: '/admin/labour-market',
        icon: BriefcaseBusiness,
        available: true,
      },
      { label: 'Users', to: '/admin/users', icon: Users, available: true },
      { label: 'Settings', to: '/admin/settings', icon: Settings, available: true },
      { label: 'Activity log', to: '/admin/audit-log', icon: History, available: true },
    ],
  },
]
