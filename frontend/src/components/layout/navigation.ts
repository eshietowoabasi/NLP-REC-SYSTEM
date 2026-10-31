import {
  BookOpen,
  BriefcaseBusiness,
  File,
  FileText,
  LayoutDashboard,
  Search,
  Settings,
  SquareCheckBig,
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

/** Sidebar structure (docs/design/skillbridge-design/pages/Sidebar.dc.html). */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'main',
    label: 'Workspace',
    items: [
      { label: 'Dashboard', to: '/', icon: LayoutDashboard, available: true },
      { label: 'Documents', to: '/documents', icon: File, available: true },
      {
        label: 'Analyses',
        to: '/sessions',
        icon: Search,
        available: true,
        alsoActive: ['/recommendations/*'],
      },
      { label: 'Reports', to: '/reports', icon: FileText, available: true },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    roles: ['admin'],
    items: [
      { label: 'Curriculum benchmarks', to: '/admin/benchmarks', icon: BookOpen, available: true },
      { label: 'Labour market', to: '/admin/labour-market', icon: BriefcaseBusiness, available: true },
      { label: 'Users', to: '/admin/users', icon: Users, available: true },
      { label: 'Settings', to: '/admin/settings', icon: Settings, available: true },
      { label: 'Activity log', to: '/admin/audit-log', icon: SquareCheckBig, available: true },
    ],
  },
]
