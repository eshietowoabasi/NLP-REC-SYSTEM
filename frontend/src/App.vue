<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const links = computed(() => [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/documents', label: 'Documents' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/reports', label: 'Reports' },
  ...(auth.isAdmin
    ? [
        { to: '/admin/users', label: 'Users' },
        { to: '/admin/audit', label: 'Audit log' },
      ]
    : []),
])

async function logout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <nav v-if="auth.isAuthenticated" class="navbar navbar-expand-lg navbar-dark bg-rs mb-4">
    <div class="container-xl">
      <RouterLink class="navbar-brand" to="/dashboard">NLP-RS <small class="d-none d-xxl-inline">Curriculum Recommendation</small></RouterLink>
      <button class="navbar-toggler" type="button" aria-label="Toggle navigation" @click="menuOpen = !menuOpen">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" :class="{ show: menuOpen }">
        <ul class="navbar-nav me-auto">
          <li v-for="link in links" :key="link.to" class="nav-item">
            <RouterLink class="nav-link text-nowrap" active-class="active" :to="link.to" @click="menuOpen = false">{{ link.label }}</RouterLink>
          </li>
        </ul>
        <span class="navbar-text me-3 small text-nowrap" data-test="current-user">
          {{ auth.user.username }} · {{ auth.user.role }}
        </span>
        <button class="btn btn-outline-light btn-sm text-nowrap" type="button" @click="logout">Sign out</button>
      </div>
    </div>
  </nav>
  <main class="container-xl pb-5">
    <RouterView />
  </main>
</template>
