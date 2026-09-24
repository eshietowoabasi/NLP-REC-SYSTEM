<script setup>
import { ref } from 'vue'
import ScoreBar from './ScoreBar.vue'
import StatusBadge from './StatusBadge.vue'
import { score } from '../utils/format'

// Spec §13.1: title, description, scores, overlap status, evidence, decision controls, notes.
const props = defineProps({
  rec: { type: Object, required: true },
  canReview: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['decide'])
const notes = ref(props.rec.planner_notes || '')
const isDuplicate = () => props.rec.overlap_status === 'Potential Duplicate'

function decide(decision) {
  emit('decide', { rec: props.rec, decision, notes: notes.value })
}
</script>

<template>
  <div class="card h-100" :data-test="`rec-${rec.rec_id}`">
    <div class="card-body d-flex flex-column">
      <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
        <h2 class="h6 mb-0 min-w-0">
          <span class="text-body-secondary me-1">#{{ rec.rank }}</span>
          <RouterLink :to="`/recommendations/${rec.rec_id}`" data-test="rec-title">{{ rec.topic_title }}</RouterLink>
        </h2>
        <span class="fs-5 fw-semibold text-nowrap" title="Composite score">{{ score(rec.composite_score) }}</span>
      </div>
      <div class="d-flex flex-wrap gap-1 mb-2">
        <StatusBadge :status="rec.overlap_status" />
        <StatusBadge :status="rec.planner_decision" data-test="decision-badge" />
      </div>
      <p class="small text-body-secondary mb-2">{{ rec.topic_description }}</p>
      <ScoreBar label="NER skill demand" :value="rec.ner_score" />
      <ScoreBar label="Topic relevance" :value="rec.topic_score" />
      <ScoreBar label="Novelty vs NUC core" :value="rec.novelty_score" />
      <div v-if="rec.evidence?.passages?.length" class="mt-2">
        <div class="small fw-semibold mb-1">Supporting evidence</div>
        <p v-for="(p, i) in rec.evidence.passages.slice(0, 2)" :key="i" class="passage small mb-1">“{{ p.text }}”</p>
      </div>
      <div v-if="canReview" class="mt-auto pt-3">
        <textarea
          v-model="notes"
          class="form-control form-control-sm mb-2"
          rows="2"
          :placeholder="isDuplicate() ? 'Justification required to accept a potential duplicate' : 'Planner notes (optional)'"
          aria-label="Planner notes"
        ></textarea>
        <div class="btn-group btn-group-sm w-100" role="group" aria-label="Decision">
          <button class="btn btn-outline-success" :disabled="busy" data-test="accept" @click="decide('Accepted')">Accept</button>
          <button class="btn btn-outline-danger" :disabled="busy" data-test="reject" @click="decide('Rejected')">Reject</button>
          <button class="btn btn-outline-warning" :disabled="busy" data-test="flag" @click="decide('Flagged')">Flag</button>
        </div>
      </div>
      <div v-else-if="rec.planner_notes" class="mt-auto pt-2 small"><strong>Notes:</strong> {{ rec.planner_notes }}</div>
    </div>
  </div>
</template>
