<script setup>
import { onMounted, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import PaginationNav from '../components/PaginationNav.vue'
import { api } from '../services/api'
import { dateTime, fileSize } from '../utils/format'

const reports = ref([])
const pagination = ref(null)
const error = ref(null)

async function load(page = 1) {
  try {
    const data = await api.get('/reports', { page, per_page: 20 })
    reports.value = data.items
    pagination.value = data.pagination
  } catch (e) {
    error.value = e
  }
}

onMounted(() => load())
</script>

<template>
  <h1 class="h3 mb-3">Reports</h1>
  <p class="small text-body-secondary">Generate a report from a completed session's page. Each report captures the configuration, corpus, NLP findings, overlap results, ranked recommendations, planner decisions and curriculum mappings at the time it was generated.</p>
  <ErrorAlert :error="error" />
  <div class="card">
    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0" data-test="reports-table">
        <thead><tr><th>Session</th><th>Format</th><th>Size</th><th>Generated</th><th></th></tr></thead>
        <tbody>
          <tr v-for="r in reports" :key="r.report_id">
            <td><RouterLink :to="`/sessions/${r.session_id}`">{{ r.session_name }}</RouterLink></td>
            <td class="text-uppercase small">{{ r.format }}</td>
            <td class="small">{{ fileSize(r.file_size) }}</td>
            <td class="small">{{ dateTime(r.created_at) }}</td>
            <td class="text-end"><a class="btn btn-sm btn-outline-primary" :href="`/api/reports/${r.report_id}/download`">Download</a></td>
          </tr>
          <tr v-if="!reports.length"><td colspan="5" class="small text-body-secondary p-3">No reports generated yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <PaginationNav :pagination="pagination" @change="load" />
</template>
