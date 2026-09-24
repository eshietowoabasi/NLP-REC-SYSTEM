<script setup>
import { onMounted, reactive, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import PaginationNav from '../components/PaginationNav.vue'
import { api } from '../services/api'
import { dateTime } from '../utils/format'

const entries = ref([])
const pagination = ref(null)
const error = ref(null)
const filters = reactive({ action_type: '', entity_type: '', from: '', to: '' })

async function load(page = 1) {
  try {
    const data = await api.get('/admin/audit', { ...filters, page, per_page: 50 })
    entries.value = data.items
    pagination.value = data.pagination
    error.value = null
  } catch (e) {
    error.value = e
  }
}

onMounted(() => load())
</script>

<template>
  <h1 class="h3 mb-3">Audit log</h1>
  <form class="row g-2 mb-3" @submit.prevent="load(1)">
    <div class="col-sm-6 col-lg-3"><input v-model="filters.action_type" class="form-control form-control-sm" placeholder="Action (e.g. LOGIN)" aria-label="Action type" /></div>
    <div class="col-sm-6 col-lg-3">
      <select v-model="filters.entity_type" class="form-select form-select-sm" aria-label="Entity type">
        <option value="">All entities</option>
        <option v-for="e in ['User', 'Document', 'AnalysisSession', 'Recommendation', 'CurriculumMap', 'Report']" :key="e">{{ e }}</option>
      </select>
    </div>
    <div class="col-sm-4 col-lg-2"><input v-model="filters.from" type="date" class="form-control form-control-sm" aria-label="From date" /></div>
    <div class="col-sm-4 col-lg-2"><input v-model="filters.to" type="date" class="form-control form-control-sm" aria-label="To date" /></div>
    <div class="col-sm-4 col-lg-2"><button class="btn btn-sm btn-primary w-100">Filter</button></div>
  </form>
  <ErrorAlert :error="error" />
  <div class="card">
    <div class="table-responsive">
      <table class="table table-sm mb-0 small">
        <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
        <tbody>
          <tr v-for="e in entries" :key="e.log_id">
            <td class="text-nowrap">{{ dateTime(e.action_timestamp) }}</td>
            <td>{{ e.username || '–' }}</td>
            <td><code>{{ e.action_type }}</code></td>
            <td>{{ e.entity_type }}{{ e.entity_id ? ` #${e.entity_id}` : '' }}</td>
            <td class="text-break"><code v-if="e.detail" class="small">{{ JSON.stringify(e.detail) }}</code></td>
          </tr>
          <tr v-if="!entries.length"><td colspan="5" class="text-body-secondary p-3">No entries.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <PaginationNav :pagination="pagination" @change="load" />
</template>
