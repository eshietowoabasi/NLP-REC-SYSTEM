<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorAlert from '../components/ErrorAlert.vue'
import PaginationNav from '../components/PaginationNav.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { dateTime } from '../utils/format'

const auth = useAuthStore()
const router = useRouter()
const sessions = ref([])
const pagination = ref(null)
const error = ref(null)
const parsedDocs = ref([])
const form = reactive({
  session_name: '',
  selected: [],
  showAdvanced: false,
  config: { similarity_threshold: 0.8, ner_weight: 0.4, topic_weight: 0.35, novelty_weight: 0.25, max_recommendations: 20 },
  busy: false,
  error: null,
})
const weightSum = computed(() => +(form.config.ner_weight + form.config.topic_weight + form.config.novelty_weight).toFixed(4))
const MAX_DOCS = 50

async function load(page = 1) {
  try {
    const data = await api.get('/sessions', { page, per_page: 15 })
    sessions.value = data.items
    pagination.value = data.pagination
  } catch (e) {
    error.value = e
  }
}

async function loadDocuments() {
  const data = await api.get('/documents', { status: 'Parsed', per_page: 100 })
  parsedDocs.value = data.items
}

async function create() {
  form.busy = true
  form.error = null
  try {
    const { session } = await api.post('/sessions', {
      session_name: form.session_name.trim(),
      document_ids: form.selected,
      parameter_config: form.config,
    })
    router.push(`/sessions/${session.session_id}`)
  } catch (e) {
    form.error = e
  } finally {
    form.busy = false
  }
}

onMounted(() => {
  load()
  if (auth.canWrite) loadDocuments().catch((e) => (error.value = e))
})
</script>

<template>
  <h1 class="h3 mb-3">Analysis sessions</h1>
  <form v-if="auth.canWrite" class="card card-body mb-4" data-test="session-form" @submit.prevent="create">
    <h2 class="h6">Create an analysis session</h2>
    <ErrorAlert :error="form.error" />
    <div class="mb-2">
      <label class="form-label small" for="session-name">Session name</label>
      <input id="session-name" v-model="form.session_name" class="form-control" required maxlength="255" placeholder="e.g. 2026 Computing Curriculum Review" />
    </div>
    <div class="mb-2">
      <div class="d-flex justify-content-between">
        <span class="form-label small">Documents to analyse ({{ form.selected.length }} of max {{ MAX_DOCS }} selected)</span>
        <button type="button" class="btn btn-link btn-sm p-0" @click="form.selected = parsedDocs.slice(0, MAX_DOCS).map((d) => d.document_id)">Select all</button>
      </div>
      <div class="border rounded p-2" style="max-height: 220px; overflow: auto">
        <div v-for="doc in parsedDocs" :key="doc.document_id" class="form-check">
          <input :id="`doc-${doc.document_id}`" v-model="form.selected" class="form-check-input" type="checkbox" :value="doc.document_id" />
          <label class="form-check-label small" :for="`doc-${doc.document_id}`">
            {{ doc.title }} <span class="text-body-secondary">· {{ doc.source_category }} · {{ doc.word_count }} words</span>
          </label>
        </div>
        <div v-if="!parsedDocs.length" class="small text-body-secondary">
          No parsed documents yet. <RouterLink to="/documents">Upload documents</RouterLink> first.
        </div>
      </div>
      <div class="form-text">NUC Core Reference documents are always used for overlap detection; selecting them is optional.</div>
    </div>
    <button type="button" class="btn btn-link btn-sm px-0 align-self-start" @click="form.showAdvanced = !form.showAdvanced">
      {{ form.showAdvanced ? 'Hide' : 'Show' }} scoring parameters
    </button>
    <div v-if="form.showAdvanced" class="row g-2 mb-2">
      <div class="col-sm-4 col-lg-2" v-for="(label, key) in { similarity_threshold: 'Overlap threshold', ner_weight: 'NER weight', topic_weight: 'Topic weight', novelty_weight: 'Novelty weight' }" :key="key">
        <label class="form-label small" :for="key">{{ label }}</label>
        <input :id="key" v-model.number="form.config[key]" class="form-control form-control-sm" type="number" step="0.05" min="0" max="1" />
      </div>
      <div class="col-sm-4 col-lg-2">
        <label class="form-label small" for="max-recs">Max recommendations</label>
        <input id="max-recs" v-model.number="form.config.max_recommendations" class="form-control form-control-sm" type="number" min="1" max="100" />
      </div>
      <div class="col-12 small" :class="weightSum === 1 ? 'text-body-secondary' : 'text-danger'">Weights sum to {{ weightSum }} (must be 1.0).</div>
    </div>
    <div>
      <button class="btn btn-primary" type="submit" :disabled="form.busy || !form.selected.length || form.selected.length > MAX_DOCS">
        {{ form.busy ? 'Creating…' : 'Create session' }}
      </button>
    </div>
  </form>

  <ErrorAlert :error="error" />
  <div class="card">
    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0">
        <thead>
          <tr><th>Session</th><th>Status</th><th>Documents</th><th>Created</th><th>Completed</th></tr>
        </thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.session_id">
            <td><RouterLink :to="`/sessions/${s.session_id}`">{{ s.session_name }}</RouterLink></td>
            <td><StatusBadge :status="s.status" /></td>
            <td class="small">{{ s.pipeline_info?.document_count ?? '–' }}</td>
            <td class="small">{{ dateTime(s.created_at) }}</td>
            <td class="small">{{ dateTime(s.completed_at) }}</td>
          </tr>
          <tr v-if="!sessions.length">
            <td colspan="5" class="text-body-secondary small p-3">No sessions yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <PaginationNav :pagination="pagination" @change="load" />
</template>
