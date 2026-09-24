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
  items: NavItem[]
}

/**
 * Sidebar structure. Screens are switched on phase by phase as they are built;
 * the Admin section is restricted to admins once authentication lands (Phase 1).
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'main',
    label: 'Workspace',
    items: [
      { label: 'Dashboard', to: '/', icon: LayoutDashboard, available: true },
      { label: 'Documents', to: '/documents', icon: FileText, available: false },
      { label: 'Analysis Sessions', to: '/sessions', icon: FlaskConical, available: false },
      { label: 'Reports', to: '/reports', icon: FileBarChart, available: false },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    items: [
      { label: 'NUC Core Reference', to: '/admin/nuc-core', icon: BookMarked, available: false },
      { label: 'Users', to: '/admin/users', icon: Users, available: false },
      { label: 'Settings', to: '/admin/settings', icon: Settings, available: false },
      { label: 'Audit Log', to: '/admin/audit-log', icon: ScrollText, available: false },
    ],
  },
]
