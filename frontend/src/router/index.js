import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Routes from spec §13. `roles` restricts a page; the API enforces the same rules.
export const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
  { path: '/documents', name: 'documents', component: () => import('../views/DocumentsView.vue') },
  { path: '/sessions', name: 'sessions', component: () => import('../views/SessionsView.vue') },
  { path: '/sessions/:id', name: 'session', component: () => import('../views/SessionDetailView.vue'), props: true },
  { path: '/sessions/:id/results', name: 'evidence', component: () => import('../views/EvidenceView.vue'), props: true },
  {
    path: '/sessions/:id/recommendations',
    name: 'recommendations',
    component: () => import('../views/RecommendationsView.vue'),
    props: true,
  },
  {
    path: '/recommendations/:id',
    name: 'recommendation',
    component: () => import('../views/RecommendationDetailView.vue'),
    props: true,
  },
  { path: '/recommendations/:id/map', name: 'mapping', component: () => import('../views/MappingView.vue'), props: true },
  { path: '/reports', name: 'reports', component: () => import('../views/ReportsView.vue') },
  { path: '/admin/users', name: 'admin-users', component: () => import('../views/AdminUsersView.vue'), meta: { roles: ['Admin'] } },
  { path: '/admin/audit', name: 'admin-audit', component: () => import('../views/AuditLogView.vue'), meta: { roles: ['Admin'] } },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue') },
]

export async function authGuard(to, auth) {
  if (!auth.checked) await auth.fetchMe()
  if (to.meta.public) return auth.isAuthenticated && to.name === 'login' ? { name: 'dashboard' } : true
  if (!auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.roles && !to.meta.roles.includes(auth.user.role)) return { name: 'dashboard' }
  return true
}

export function createAppRouter() {
  const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })
  router.beforeEach((to) => authGuard(to, useAuthStore()))
  return router
}
