<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorAlert from '../components/ErrorAlert.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { PIPELINE_STAGE_LABELS, dateTime } from '../utils/format'

const props = defineProps({ id: { type: String, required: true } })
const auth = useAuthStore()
const router = useRouter()
const session = ref(null)
const documents = ref({})
const error = ref(null)
const busy = ref(false)
const reportBusy = ref('')
let timer = null

const stages = Object.keys(PIPELINE_STAGE_LABELS)
const canReview = computed(() => auth.canReview(session.value))
const runnable = computed(() => ['Pending', 'Failed'].includes(session.value?.status))

async function load() {
  try {
    session.value = (await api.get(`/sessions/${props.id}`)).session
    error.value = null
    const missing = session.value.document_ids.filter((id) => !documents.value[id])
    await Promise.all(
      missing.map(async (id) => {
        try {
          documents.value[id] = (await api.get(`/documents/${id}`)).document
        } catch {
          documents.value[id] = { document_id: id, title: `Document ${id} (deleted)` }
        }
      }),
    )
  } catch (e) {
    error.value = e
  }
  schedulePoll()
}

// Poll while the background job runs (docs/DECISIONS.md, D3).
function schedulePoll() {
  clearTimeout(timer)
  if (session.value?.status === 'Processing') timer = setTimeout(load, 2500)
}

async function run() {
  busy.value = true
  try {
    await api.post(`/sessions/${props.id}/run`)
    await load()
  } catch (e) {
    error.value = e
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!window.confirm('Delete this session and all its results?')) return
  try {
    await api.delete(`/sessions/${props.id}`)
    router.push('/sessions')
  } catch (e) {
    error.value = e
  }
}

async function generateReport(format) {
  reportBusy.value = format
  try {
    const { report } = await api.post(`/sessions/${props.id}/reports`, { format })
    window.location.href = `/api/reports/${report.report_id}/download`
  } catch (e) {
    error.value = e
  } finally {
    reportBusy.value = ''
  }
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <ErrorAlert :error="error" />
  <template v-if="session">
    <nav class="small mb-2"><RouterLink to="/sessions">Analysis sessions</RouterLink> / {{ session.session_name }}</nav>
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
      <h1 class="h3 mb-0">{{ session.session_name }} <StatusBadge :status="session.status" data-test="session-status" /></h1>
      <div class="d-flex gap-2">
        <button v-if="canReview && runnable" class="btn btn-primary" :disabled="busy" data-test="run" @click="run">
          {{ session.status === 'Failed' ? 'Retry analysis' : 'Run analysis' }}
        </button>
        <button v-if="canReview && session.status !== 'Processing'" class="btn btn-outline-danger" @click="remove">Delete</button>
      </div>
    </div>

    <div v-if="session.status === 'Processing'" class="card card-body mb-3" data-test="progress">
      <div class="d-flex align-items-center gap-2 mb-2">
        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
        <strong>{{ PIPELINE_STAGE_LABELS[session.progress.stage] || 'Working' }}…</strong>
      </div>
      <div class="progress" role="progressbar" :aria-valuenow="session.progress.step || 0" aria-valuemin="0" :aria-valuemax="session.progress.total_steps">
        <div class="progress-bar" :style="{ width: `${((session.progress.step || 0) / session.progress.total_steps) * 100}%` }"></div>
      </div>
      <ol class="small text-body-secondary mt-2 mb-0 ps-3">
        <li v-for="(stage, i) in stages.slice(1)" :key="stage" :class="{ 'fw-semibold text-body': i + 1 === session.progress.step }">
          {{ PIPELINE_STAGE_LABELS[stage] }}
        </li>
      </ol>
    </div>
    <div v-if="session.status === 'Failed'" class="alert alert-danger" data-test="failure">
      <strong>The analysis failed.</strong> {{ session.error_message }}
    </div>

    <div v-if="session.status === 'Completed'" class="card card-body mb-3">
      <div class="d-flex flex-wrap gap-2">
        <RouterLink :to="`/sessions/${id}/recommendations`" class="btn btn-primary" data-test="view-recommendations">
          View {{ session.pipeline_info?.recommendation_count ?? '' }} recommendations
        </RouterLink>
        <RouterLink :to="`/sessions/${id}/results`" class="btn btn-outline-primary">Evidence dashboard</RouterLink>
        <template v-if="auth.canWrite">
          <button class="btn btn-outline-secondary" :disabled="!!reportBusy" data-test="report-pdf" @click="generateReport('pdf')">
            {{ reportBusy === 'pdf' ? 'Generating…' : 'Download PDF report' }}
          </button>
          <button class="btn btn-outline-secondary" :disabled="!!reportBusy" @click="generateReport('docx')">
            {{ reportBusy === 'docx' ? 'Generating…' : 'Download DOCX report' }}
          </button>
        </template>
      </div>
      <div v-for="w in session.pipeline_info?.warnings || []" :key="w" class="alert alert-warning small mt-3 mb-0">{{ w }}</div>
    </div>

    <div class="row g-3">
      <div class="col-lg-7">
        <div class="card">
          <div class="card-header bg-white fw-semibold">Input documents</div>
          <ul class="list-group list-group-flush">
            <li v-for="docId in session.document_ids" :key="docId" class="list-group-item small d-flex justify-content-between">
              <span>{{ documents[docId]?.title || '…' }}</span>
              <span class="text-body-secondary">{{ documents[docId]?.source_category }}</span>
            </li>
          </ul>
        </div>
      </div>
      <div class="col-lg-5">
        <div class="card">
          <div class="card-header bg-white fw-semibold">Configuration</div>
          <table class="table table-sm mb-0 small">
            <tbody>
              <tr><th>Overlap threshold</th><td>{{ session.parameter_config.similarity_threshold }}</td></tr>
              <tr>
                <th>Weights (NER / topic / novelty)</th>
                <td>{{ session.parameter_config.ner_weight }} / {{ session.parameter_config.topic_weight }} / {{ session.parameter_config.novelty_weight }}</td>
              </tr>
              <tr><th>Max recommendations</th><td>{{ session.parameter_config.max_recommendations }}</td></tr>
              <tr><th>Created</th><td>{{ dateTime(session.created_at) }}</td></tr>
              <tr v-if="session.completed_at"><th>Completed</th><td>{{ dateTime(session.completed_at) }}</td></tr>
              <template v-if="session.pipeline_info">
                <tr><th>Processing time</th><td>{{ session.pipeline_info.total_seconds }} s</td></tr>
                <tr><th>Embedding model</th><td>{{ session.pipeline_info.embedding_model }}</td></tr>
                <tr><th>Passages / topics</th><td>{{ session.pipeline_info.passage_count }} / {{ session.pipeline_info.topic_count }}</td></tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </template>
</template>
