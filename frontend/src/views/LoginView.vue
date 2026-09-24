<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ErrorAlert from '../components/ErrorAlert.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const error = ref(null)
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = null
  try {
    await auth.login(username.value.trim(), password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/dashboard'
    router.replace(next)
  } catch (e) {
    error.value = e
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="row justify-content-center pt-5">
    <div class="col-sm-9 col-md-6 col-lg-4">
      <div class="text-center mb-4">
        <h1 class="h3 mb-1">NLP-RS</h1>
        <p class="text-body-secondary small mb-0">NLP-Driven Curriculum Recommendation System</p>
        <p class="text-body-secondary small">Department of Computer Science, University of Uyo</p>
      </div>
      <form class="card card-body" @submit.prevent="submit">
        <ErrorAlert :error="error" />
        <div class="mb-3">
          <label class="form-label" for="username">Username</label>
          <input id="username" v-model="username" class="form-control" autocomplete="username" required autofocus />
        </div>
        <div class="mb-3">
          <label class="form-label" for="password">Password</label>
          <input id="password" v-model="password" type="password" class="form-control" autocomplete="current-password" required />
        </div>
        <button class="btn btn-primary w-100" type="submit" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
      </form>
    </div>
  </div>
</template>
