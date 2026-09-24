<script setup>
import { onMounted, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { dateTime } from '../utils/format'

const auth = useAuthStore()
const summary = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    summary.value = await api.get('/dashboard/summary')
  } catch (e) {
    error.value = e
  }
})
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h3 mb-0">Dashboard</h1>
    <RouterLink v-if="auth.canWrite" to="/sessions" class="btn btn-primary">New analysis</RouterLink>
  </div>
  <ErrorAlert :error="error" />
  <template v-if="summary">
    <div v-if="!summary.core_reference_available" class="alert alert-warning" data-test="core-warning">
      No NUC Core Reference document has been uploaded yet. Analyses cannot check overlap with the 70% core until an
      Admin uploads the CCMAS core curriculum.
    </div>
    <div class="row g-3 mb-4">
      <div class="col-sm-6 col-lg-3">
        <div class="card card-body">
          <div class="text-body-secondary small">Source documents</div>
          <div class="stat-value" data-test="stat-documents">{{ summary.documents.total }}</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="card card-body">
          <div class="text-body-secondary small">Analysis sessions</div>
          <div class="stat-value">{{ summary.sessions.total }}</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="card card-body">
          <div class="text-body-secondary small">Completed analyses</div>
          <div class="stat-value">{{ summary.sessions.by_status.Completed }}</div>
        </div>
      </div>
      <div class="col-sm-6 col-lg-3">
        <div class="card card-body">
          <div class="text-body-secondary small">My recommendations awaiting review</div>
          <div class="stat-value">{{ summary.my_pending_reviews }}</div>
        </div>
      </div>
    </div>
    <div class="row g-3">
      <div class="col-lg-8">
        <div class="card">
          <div class="card-header bg-white fw-semibold">Recent sessions</div>
          <div class="table-responsive">
            <table class="table table-sm mb-0">
              <thead>
                <tr><th>Session</th><th>Status</th><th>Created</th></tr>
              </thead>
              <tbody>
                <tr v-for="s in summary.recent_sessions" :key="s.session_id">
                  <td><RouterLink :to="`/sessions/${s.session_id}`">{{ s.session_name }}</RouterLink></td>
                  <td><StatusBadge :status="s.status" /></td>
                  <td class="small">{{ dateTime(s.created_at) }}</td>
                </tr>
                <tr v-if="!summary.recent_sessions.length">
                  <td colspan="3" class="text-body-secondary small">No sessions yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card">
          <div class="card-header bg-white fw-semibold">Documents by source</div>
          <ul class="list-group list-group-flush">
            <li v-for="(count, category) in summary.documents.by_category" :key="category" class="list-group-item d-flex justify-content-between small">
              <span>{{ category }}</span><span class="fw-semibold">{{ count }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </template>
</template>
