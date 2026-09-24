<script setup>
import { onMounted, reactive, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import PaginationNav from '../components/PaginationNav.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { SOURCE_CATEGORIES, dateTime, fileSize } from '../utils/format'

const auth = useAuthStore()
const documents = ref([])
const pagination = ref(null)
const filters = reactive({ source_category: '', status: '', q: '', page: 1 })
const error = ref(null)
const notice = ref('')

const upload = reactive({ file: null, title: '', source_category: 'Job Market Data', busy: false, error: null })
const fileInput = ref(null)
const preview = reactive({ id: null, text: '', view: 'clean' })

const categories = () => SOURCE_CATEGORIES.filter((c) => c !== 'NUC Core Reference' || auth.isAdmin)

async function load(page = filters.page) {
  filters.page = page
  try {
    const data = await api.get('/documents', { ...filters, per_page: 15 })
    documents.value = data.items
    pagination.value = data.pagination
    error.value = null
  } catch (e) {
    error.value = e
  }
}

async function submitUpload() {
  if (!upload.file) return
  upload.busy = true
  upload.error = null
  notice.value = ''
  const form = new FormData()
  form.append('file', upload.file)
  form.append('source_category', upload.source_category)
  if (upload.title.trim()) form.append('title', upload.title.trim())
  try {
    const { document } = await api.upload('/documents', form)
    notice.value =
      document.processing_status === 'Parsed'
        ? `Uploaded “${document.title}” (${document.word_count} words).`
        : `Uploaded “${document.title}”, but text extraction failed: ${document.error_message}`
    upload.file = null
    upload.title = ''
    if (fileInput.value) fileInput.value.value = ''
    await load(1)
  } catch (e) {
    upload.error = e
  } finally {
    upload.busy = false
  }
}

async function remove(doc) {
  if (!window.confirm(`Delete “${doc.title}”? This cannot be undone.`)) return
  try {
    await api.delete(`/documents/${doc.document_id}`)
    await load()
  } catch (e) {
    error.value = e
  }
}

async function togglePreview(doc, view = 'clean') {
  if (preview.id === doc.document_id && preview.view === view) {
    preview.id = null
    return
  }
  try {
    const data = await api.get(`/documents/${doc.document_id}/text`, { view })
    Object.assign(preview, { id: doc.document_id, text: data.text, view })
  } catch (e) {
    error.value = e
  }
}

const canDelete = (doc) => auth.isAdmin || (auth.canWrite && doc.user_id === auth.user.user_id && doc.source_category !== 'NUC Core Reference')

onMounted(() => load())
</script>

<template>
  <h1 class="h3 mb-3">Document library</h1>
  <form v-if="auth.canWrite" class="card card-body mb-4" data-test="upload-form" @submit.prevent="submitUpload">
    <h2 class="h6">Upload a source document</h2>
    <ErrorAlert :error="upload.error" />
    <div v-if="notice" class="alert alert-success py-2" data-test="upload-notice">{{ notice }}</div>
    <div class="row g-2 align-items-end">
      <div class="col-md-4">
        <label class="form-label small" for="file">File (PDF, DOCX or TXT, max 25 MB)</label>
        <input id="file" ref="fileInput" class="form-control" type="file" accept=".pdf,.docx,.txt" required @change="upload.file = $event.target.files[0] || null" />
      </div>
      <div class="col-md-3">
        <label class="form-label small" for="category">Source category</label>
        <select id="category" v-model="upload.source_category" class="form-select">
          <option v-for="c in categories()" :key="c">{{ c }}</option>
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label small" for="title">Title (optional)</label>
        <input id="title" v-model="upload.title" class="form-control" maxlength="255" placeholder="Defaults to file name" />
      </div>
      <div class="col-md-2">
        <button class="btn btn-primary w-100" type="submit" :disabled="upload.busy || !upload.file">
          {{ upload.busy ? 'Uploading…' : 'Upload' }}
        </button>
      </div>
    </div>
  </form>

  <div class="row g-2 mb-2">
    <div class="col-md-4">
      <input v-model="filters.q" class="form-control form-control-sm" placeholder="Search titles" aria-label="Search titles" @keyup.enter="load(1)" />
    </div>
    <div class="col-md-3">
      <select v-model="filters.source_category" class="form-select form-select-sm" aria-label="Filter by category" @change="load(1)">
        <option value="">All categories</option>
        <option v-for="c in SOURCE_CATEGORIES" :key="c">{{ c }}</option>
      </select>
    </div>
    <div class="col-md-2">
      <select v-model="filters.status" class="form-select form-select-sm" aria-label="Filter by status" @change="load(1)">
        <option value="">Any status</option>
        <option>Parsed</option>
        <option>Failed</option>
      </select>
    </div>
  </div>
  <ErrorAlert :error="error" />
  <div class="card">
    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0" data-test="documents-table">
        <thead>
          <tr><th>Title</th><th>Category</th><th>Status</th><th>Words</th><th>Size</th><th>Uploaded</th><th></th></tr>
        </thead>
        <tbody>
          <template v-for="doc in documents" :key="doc.document_id">
            <tr>
              <td>
                {{ doc.title }}
                <div class="small text-body-secondary">{{ doc.original_filename }}</div>
                <div v-if="doc.error_message" class="small text-danger">{{ doc.error_message }}</div>
              </td>
              <td class="small">{{ doc.source_category }}</td>
              <td><StatusBadge :status="doc.processing_status" /></td>
              <td class="small">{{ doc.word_count ?? '–' }}</td>
              <td class="small">{{ fileSize(doc.file_size) }}</td>
              <td class="small">{{ dateTime(doc.upload_timestamp) }}</td>
              <td class="text-end text-nowrap">
                <button v-if="doc.processing_status === 'Parsed'" class="btn btn-sm btn-link" @click="togglePreview(doc)">Text</button>
                <button v-if="canDelete(doc)" class="btn btn-sm btn-link text-danger" @click="remove(doc)">Delete</button>
              </td>
            </tr>
            <tr v-if="preview.id === doc.document_id">
              <td colspan="7">
                <div class="d-flex gap-2 mb-2 small">
                  <span>Showing {{ preview.view === 'clean' ? 'cleaned' : 'raw extracted' }} text.</span>
                  <button class="btn btn-sm btn-link p-0" @click="togglePreview(doc, preview.view === 'clean' ? 'raw' : 'clean')">
                    Show {{ preview.view === 'clean' ? 'raw' : 'cleaned' }}
                  </button>
                </div>
                <pre class="small bg-light p-2 mb-0" style="max-height: 300px; white-space: pre-wrap">{{ preview.text }}</pre>
              </td>
            </tr>
          </template>
          <tr v-if="!documents.length">
            <td colspan="7" class="text-body-secondary small p-3">No documents found.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <PaginationNav :pagination="pagination" @change="load" />
</template>
