<script setup>
import { onMounted, reactive, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import { api } from '../services/api'
import { ROLES, useAuthStore } from '../stores/auth'
import { dateTime } from '../utils/format'

const auth = useAuthStore()
const users = ref([])
const error = ref(null)
const notice = ref('')
const form = reactive({ username: '', email: '', password: '', role: ROLES.PLANNER, error: null })

async function load() {
  try {
    users.value = (await api.get('/admin/users', { per_page: 100 })).items
  } catch (e) {
    error.value = e
  }
}

async function create() {
  form.error = null
  try {
    const { user } = await api.post('/admin/users', { username: form.username, email: form.email, password: form.password, role: form.role })
    notice.value = `Created ${user.username}.`
    Object.assign(form, { username: '', email: '', password: '' })
    await load()
  } catch (e) {
    form.error = e
  }
}

async function update(user, changes, message) {
  error.value = null
  try {
    Object.assign(user, (await api.patch(`/admin/users/${user.user_id}`, changes)).user)
    notice.value = message
  } catch (e) {
    error.value = e
    await load()
  }
}

function resetPassword(user) {
  const password = window.prompt(`New password for ${user.username} (at least 8 characters):`)
  if (password) update(user, { password }, `Password reset for ${user.username}.`)
}

onMounted(load)
</script>

<template>
  <h1 class="h3 mb-3">User management</h1>
  <div v-if="notice" class="alert alert-success py-2">{{ notice }}</div>
  <form class="card card-body mb-4" data-test="user-form" @submit.prevent="create">
    <h2 class="h6">Add a user</h2>
    <ErrorAlert :error="form.error" />
    <div class="row g-2 align-items-end">
      <div class="col-md-3"><label class="form-label small" for="u-name">Username</label><input id="u-name" v-model="form.username" class="form-control" required /></div>
      <div class="col-md-3"><label class="form-label small" for="u-email">Email</label><input id="u-email" v-model="form.email" type="email" class="form-control" required /></div>
      <div class="col-md-2"><label class="form-label small" for="u-pass">Password</label><input id="u-pass" v-model="form.password" type="password" minlength="8" class="form-control" required autocomplete="new-password" /></div>
      <div class="col-md-2">
        <label class="form-label small" for="u-role">Role</label>
        <select id="u-role" v-model="form.role" class="form-select"><option v-for="r in Object.values(ROLES)" :key="r">{{ r }}</option></select>
      </div>
      <div class="col-md-2"><button class="btn btn-primary w-100">Add user</button></div>
    </div>
  </form>
  <ErrorAlert :error="error" />
  <div class="card">
    <div class="table-responsive">
      <table class="table table-sm mb-0">
        <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.user_id">
            <td>{{ u.username }}<div class="small text-body-secondary">{{ u.email }}</div></td>
            <td>
              <select class="form-select form-select-sm w-auto" :value="u.role" :disabled="u.user_id === auth.user.user_id" :aria-label="`Role for ${u.username}`" @change="update(u, { role: $event.target.value }, `${u.username} is now ${$event.target.value}.`)">
                <option v-for="r in Object.values(ROLES)" :key="r">{{ r }}</option>
              </select>
            </td>
            <td><span class="badge" :class="u.is_active ? 'text-bg-success' : 'text-bg-secondary'">{{ u.is_active ? 'Active' : 'Deactivated' }}</span></td>
            <td class="small">{{ dateTime(u.created_at) }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-link" @click="resetPassword(u)">Reset password</button>
              <button v-if="u.user_id !== auth.user.user_id" class="btn btn-sm btn-link" @click="update(u, { is_active: !u.is_active }, `${u.username} ${u.is_active ? 'deactivated' : 'reactivated'}.`)">
                {{ u.is_active ? 'Deactivate' : 'Reactivate' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
