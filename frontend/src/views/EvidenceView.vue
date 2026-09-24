<script setup>
import { computed, onMounted, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api } from '../services/api'
import { score } from '../utils/format'

// Evidence dashboard (spec §13 /sessions/:id/results): keywords, entities, topics, similarity.
const props = defineProps({ id: { type: String, required: true } })
const tab = ref('skills')
const data = ref({})
const error = ref(null)
const labelFilter = ref('')

const tabs = { skills: 'Skill demand (NER)', keywords: 'Keywords (TF-IDF)', topics: 'Themes (BERTopic)', similarity: 'Overlap with NUC core' }
const endpoints = { skills: 'entities', keywords: 'keywords', topics: 'topics', similarity: 'similarity' }

async function show(name) {
  tab.value = name
  if (data.value[name]) return
  try {
    data.value[name] = await api.get(`/sessions/${props.id}/${endpoints[name]}`)
  } catch (e) {
    error.value = e
  }
}

const skills = computed(() => (data.value.skills?.skill_demand || []).filter((e) => !labelFilter.value || e.label === labelFilter.value))
const maxMentions = computed(() => Math.max(1, ...skills.value.map((e) => e.mentions)))
const maxKeyword = computed(() => Math.max(1e-9, ...(data.value.keywords?.corpus_keywords || []).map((k) => k.score)))

onMounted(() => show('skills'))
</script>

<template>
  <nav class="small mb-2"><RouterLink :to="`/sessions/${id}`">Session</RouterLink> / Evidence dashboard</nav>
  <h1 class="h3 mb-3">Evidence dashboard</h1>
  <ul class="nav nav-tabs mb-3">
    <li v-for="(label, name) in tabs" :key="name" class="nav-item">
      <button class="nav-link" :class="{ active: tab === name }" :data-test="`tab-${name}`" @click="show(name)">{{ label }}</button>
    </li>
  </ul>
  <ErrorAlert :error="error" />

  <div v-if="tab === 'skills' && data.skills" class="card card-body">
    <div class="d-flex gap-2 mb-3 small align-items-center">
      <span>Show:</span>
      <select v-model="labelFilter" class="form-select form-select-sm w-auto" aria-label="Entity type">
        <option value="">Skills, tools and certifications</option>
        <option value="SKILL">Skills</option>
        <option value="TOOL">Tools</option>
        <option value="CERT">Certifications</option>
      </select>
    </div>
    <table class="table table-sm">
      <thead><tr><th>Name</th><th>Type</th><th>Documents</th><th style="width: 40%">Mentions</th></tr></thead>
      <tbody>
        <tr v-for="e in skills.slice(0, 40)" :key="e.text + e.label">
          <td>{{ e.text }}</td>
          <td class="small">{{ e.label }}</td>
          <td class="small">{{ e.document_frequency }}</td>
          <td>
            <div class="d-flex align-items-center gap-2">
              <div class="score-bar flex-grow-1"><div :style="{ width: `${(e.mentions / maxMentions) * 100}%` }"></div></div>
              <span class="small">{{ e.mentions }}</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="tab === 'keywords' && data.keywords" class="row g-3">
    <div class="col-lg-5">
      <div class="card card-body">
        <h2 class="h6">Corpus keywords</h2>
        <div v-for="k in data.keywords.corpus_keywords.slice(0, 30)" :key="k.term" class="d-flex align-items-center gap-2 small mb-1">
          <span style="width: 45%">{{ k.term }}</span>
          <div class="score-bar flex-grow-1"><div :style="{ width: `${(k.score / maxKeyword) * 100}%` }"></div></div>
        </div>
      </div>
    </div>
    <div class="col-lg-7">
      <div v-for="d in data.keywords.documents" :key="d.document_id" class="card card-body mb-2">
        <div class="small fw-semibold">{{ d.title }} <span class="text-body-secondary fw-normal">· {{ d.source_category }}</span></div>
        <div class="small">{{ d.keywords.slice(0, 12).map((k) => k.term).join(', ') || '–' }}</div>
      </div>
    </div>
  </div>

  <div v-if="tab === 'topics' && data.topics">
    <p class="small text-body-secondary">{{ data.topics.topics.length }} themes from {{ data.topics.passage_count }} passages ({{ data.topics.outlier_passages }} unclustered).</p>
    <div class="row g-3">
      <div v-for="t in data.topics.topics" :key="t.topic_id" class="col-md-6 col-xl-4">
        <div class="card card-body h-100">
          <div class="d-flex justify-content-between"><h2 class="h6">{{ t.label }}</h2><span class="small text-body-secondary">{{ t.size }} passages</span></div>
          <div class="small mb-2">{{ t.keywords.slice(0, 8).map((k) => k.term).join(', ') }}</div>
          <p v-for="(p, i) in t.representative_passages.slice(0, 2)" :key="i" class="passage small mb-1">“{{ p.text }}”</p>
        </div>
      </div>
    </div>
  </div>

  <div v-if="tab === 'similarity' && data.similarity" class="card card-body">
    <p class="small">Threshold: similarity above <strong>{{ data.similarity.similarity_threshold }}</strong> is a potential duplicate of the NUC core ({{ data.similarity.core_segment_count }} core segments compared).</p>
    <table class="table table-sm">
      <thead><tr><th>Recommendation</th><th>Max similarity</th><th>Status</th><th>Closest NUC core content</th></tr></thead>
      <tbody>
        <tr v-for="item in data.similarity.items" :key="item.rec_id">
          <td><RouterLink :to="`/recommendations/${item.rec_id}`">{{ item.topic_title }}</RouterLink></td>
          <td>{{ score(item.max_similarity) }}</td>
          <td><StatusBadge :status="item.overlap_status" /></td>
          <td class="small">{{ item.core_matches[0]?.text }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
