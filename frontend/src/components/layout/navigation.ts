import {
  BookMarked,
  FileText,
  FlaskConical,
  LayoutDashboard,
  ScrollText,
  Settings,
  Users,
  FileBarChart,
  type LucideIcon,
} from 'lucide-react'

import type { UserRole } from '@/types/api'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** False until the screen exists; the sidebar shows the item disabled. */
  available: boolean
}

export interface NavSection {
  id: 'main' | 'admin'
  label: string
  /** Roles that see this section; omitted means everyone. Cosmetic only: the API enforces. */
  roles?: UserRole[]
  items: NavItem[]
}

/** Sidebar structure. Screens are switched on phase by phase as they are built. */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'main',
    label: 'Workspace',
    items: [
      { label: 'Dashboard', to: '/', icon: LayoutDashboard, available: true },
      { label: 'Documents', to: '/documents', icon: FileText, available: true },
      { label: 'Analysis Sessions', to: '/sessions', icon: FlaskConical, available: true },
      { label: 'Reports', to: '/reports', icon: FileBarChart, available: true },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    roles: ['admin'],
    items: [
      { label: 'NUC Core Reference', to: '/admin/nuc-core', icon: BookMarked, available: true },
      { label: 'Users', to: '/admin/users', icon: Users, available: true },
      { label: 'Settings', to: '/admin/settings', icon: Settings, available: true },
      { label: 'Audit Log', to: '/admin/audit-log', icon: ScrollText, available: true },
    ],
  },
]
