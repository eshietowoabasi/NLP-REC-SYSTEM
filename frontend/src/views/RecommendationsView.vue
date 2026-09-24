<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({ id: { type: String, required: true } })
const auth = useAuthStore()
const session = ref(null)
const recs = ref([])
const filters = reactive({ overlap_status: '', decision: '' })
const error = ref(null)
const busyId = ref(null)
const canReview = computed(() => auth.canReview(session.value))
const counts = computed(() => {
  const c = { Accepted: 0, Rejected: 0, Flagged: 0, pending: 0 }
  recs.value.forEach((r) => (r.planner_decision ? c[r.planner_decision]++ : c.pending++))
  return c
})

async function load() {
  try {
    session.value = (await api.get(`/sessions/${props.id}`)).session
    const data = await api.get(`/sessions/${props.id}/recommendations`, { ...filters, include_evidence: 1 })
    recs.value = data.items
    error.value = null
  } catch (e) {
    error.value = e
  }
}

async function decide({ rec, decision, notes }) {
  busyId.value = rec.rec_id
  try {
    const { recommendation } = await api.patch(`/recommendations/${rec.rec_id}/decision`, { decision, notes })
    Object.assign(rec, recommendation)
    error.value = null
  } catch (e) {
    error.value = e
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <nav class="small mb-2"><RouterLink :to="`/sessions/${id}`">{{ session?.session_name || 'Session' }}</RouterLink> / Recommendations</nav>
  <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
    <h1 class="h3 mb-0">Recommendations</h1>
    <div class="small text-body-secondary" data-test="decision-counts">
      {{ counts.Accepted }} accepted · {{ counts.Rejected }} rejected · {{ counts.Flagged }} flagged · {{ counts.pending }} pending
    </div>
  </div>
  <div class="row g-2 mb-3">
    <div class="col-sm-4 col-lg-3">
      <select v-model="filters.overlap_status" class="form-select form-select-sm" aria-label="Overlap status" @change="load">
        <option value="">All overlap statuses</option>
        <option>No Significant Overlap</option>
        <option>Potential Duplicate</option>
      </select>
    </div>
    <div class="col-sm-4 col-lg-3">
      <select v-model="filters.decision" class="form-select form-select-sm" aria-label="Decision" @change="load">
        <option value="">All decisions</option>
        <option value="pending">Pending review</option>
        <option>Accepted</option>
        <option>Rejected</option>
        <option>Flagged</option>
      </select>
    </div>
  </div>
  <ErrorAlert :error="error" />
  <p class="small text-body-secondary">
    Composite = 0.40 × NER + 0.35 × topic + 0.25 × novelty (session weights apply). Potential duplicates of the NUC 70% core are
    listed after novel topics and need a justification to accept.
  </p>
  <div class="row g-3">
    <div v-for="rec in recs" :key="rec.rec_id" class="col-md-6 col-xl-4">
      <RecommendationCard :rec="rec" :can-review="canReview" :busy="busyId === rec.rec_id" @decide="decide" />
    </div>
    <div v-if="!recs.length && !error" class="text-body-secondary small">No recommendations match these filters.</div>
  </div>
</template>
