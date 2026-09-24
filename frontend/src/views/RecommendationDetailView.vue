<script setup>
import { computed, onMounted, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import ScoreBar from '../components/ScoreBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { score } from '../utils/format'

const props = defineProps({ id: { type: String, required: true } })
const auth = useAuthStore()
const rec = ref(null)
const session = ref(null)
const mappings = ref([])
const error = ref(null)
const editing = ref(false)
const title = ref('')
const notes = ref('')
const canReview = computed(() => auth.canReview(session.value))

async function load() {
  try {
    rec.value = (await api.get(`/recommendations/${props.id}`)).recommendation
    session.value = (await api.get(`/sessions/${rec.value.session_id}`)).session
    mappings.value = (await api.get(`/recommendations/${props.id}/mapping`)).items
    notes.value = rec.value.planner_notes || ''
    title.value = rec.value.topic_title
  } catch (e) {
    error.value = e
  }
}

async function decide(decision) {
  try {
    const { recommendation } = await api.patch(`/recommendations/${props.id}/decision`, { decision, notes: notes.value })
    Object.assign(rec.value, recommendation)
    error.value = null
  } catch (e) {
    error.value = e
  }
}

async function saveTitle() {
  try {
    const { recommendation } = await api.patch(`/recommendations/${props.id}`, { topic_title: title.value })
    rec.value.topic_title = recommendation.topic_title
    editing.value = false
  } catch (e) {
    error.value = e
  }
}

onMounted(load)
</script>

<template>
  <ErrorAlert :error="error" />
  <template v-if="rec">
    <nav class="small mb-2">
      <RouterLink :to="`/sessions/${rec.session_id}/recommendations`">{{ session?.session_name || 'Recommendations' }}</RouterLink> / #{{ rec.rank }}
    </nav>
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
      <template v-if="!editing">
        <h1 class="h3 mb-0" data-test="rec-heading">{{ rec.topic_title }}</h1>
        <button v-if="canReview" class="btn btn-sm btn-link" @click="editing = true">Rename</button>
      </template>
      <form v-else class="d-flex gap-2 flex-grow-1" @submit.prevent="saveTitle">
        <input v-model="title" class="form-control" maxlength="255" required aria-label="Recommendation title" />
        <button class="btn btn-primary btn-sm">Save</button>
        <button type="button" class="btn btn-outline-secondary btn-sm" @click="editing = false">Cancel</button>
      </form>
    </div>
    <div class="d-flex gap-1 mb-3">
      <StatusBadge :status="rec.overlap_status" />
      <StatusBadge :status="rec.planner_decision" />
    </div>
    <div class="row g-3">
      <div class="col-lg-8">
        <div class="card card-body mb-3">
          <p class="mb-2">{{ rec.topic_description }}</p>
          <div class="small text-body-secondary">Keywords: {{ rec.evidence.keywords.join(', ') }}</div>
        </div>
        <div class="card card-body mb-3">
          <h2 class="h6">Supporting passages</h2>
          <p v-for="(p, i) in rec.evidence.passages" :key="i" class="passage small">“{{ p.text }}”</p>
          <h2 class="h6 mt-2">Skills and tools in this theme</h2>
          <div class="d-flex flex-wrap gap-1">
            <span v-for="s in rec.evidence.skills" :key="s.text" class="badge text-bg-light border">{{ s.text }} · {{ s.mentions }}</span>
            <span v-if="!rec.evidence.skills.length" class="small text-body-secondary">None detected.</span>
          </div>
        </div>
        <div class="card card-body">
          <h2 class="h6">Closest NUC core content</h2>
          <table class="table table-sm small mb-0">
            <thead><tr><th>Similarity</th><th>Core segment</th><th>Document</th></tr></thead>
            <tbody>
              <tr v-for="(m, i) in rec.evidence.core_matches" :key="i">
                <td>{{ score(m.similarity) }}</td>
                <td>{{ m.text }}</td>
                <td>{{ m.document_title }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card card-body mb-3">
          <div class="d-flex justify-content-between mb-2"><span>Composite score</span><strong class="fs-5">{{ score(rec.composite_score) }}</strong></div>
          <ScoreBar label="NER skill demand" :value="rec.ner_score" />
          <ScoreBar label="Topic relevance" :value="rec.topic_score" />
          <ScoreBar label="Novelty vs NUC core" :value="rec.novelty_score" />
          <div class="small text-body-secondary mt-1">Max similarity to core: {{ score(rec.max_similarity) }}</div>
        </div>
        <div v-if="canReview" class="card card-body mb-3">
          <h2 class="h6">Planner decision</h2>
          <textarea v-model="notes" class="form-control form-control-sm mb-2" rows="3" aria-label="Planner notes" placeholder="Notes / justification"></textarea>
          <div class="btn-group btn-group-sm w-100">
            <button class="btn btn-outline-success" @click="decide('Accepted')">Accept</button>
            <button class="btn btn-outline-danger" @click="decide('Rejected')">Reject</button>
            <button class="btn btn-outline-warning" @click="decide('Flagged')">Flag</button>
          </div>
        </div>
        <div class="card card-body">
          <h2 class="h6">Curriculum mapping</h2>
          <ul class="list-unstyled small mb-2">
            <li v-for="m in mappings" :key="m.map_id"><strong>{{ m.course_code }}</strong> {{ m.course_title }} ({{ m.credit_units }} units)</li>
            <li v-if="!mappings.length" class="text-body-secondary">Not mapped to a course.</li>
          </ul>
          <RouterLink v-if="canReview && rec.planner_decision === 'Accepted'" :to="`/recommendations/${rec.rec_id}/map`" class="btn btn-sm btn-primary" data-test="map-link">
            {{ mappings.length ? 'Edit mapping' : 'Map to a course' }}
          </RouterLink>
          <div v-else-if="canReview" class="small text-body-secondary">Accept the recommendation to map it to a course.</div>
        </div>
      </div>
    </div>
  </template>
</template>
