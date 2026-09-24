<script setup>
import { onMounted, reactive, ref } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import { api } from '../services/api'

// Convert an accepted recommendation into a proposed course (spec §16).
const props = defineProps({ id: { type: String, required: true } })
const rec = ref(null)
const mappings = ref([])
const error = ref(null)
const saved = ref('')
const empty = () => ({ map_id: null, course_code: '', course_title: '', credit_units: 3, prerequisites: '', learning_outcomes: [''] })
const form = reactive(empty())
const reset = () => Object.assign(form, empty())

async function load() {
  try {
    rec.value = (await api.get(`/recommendations/${props.id}`)).recommendation
    mappings.value = (await api.get(`/recommendations/${props.id}/mapping`)).items
    if (!form.course_title) form.course_title = rec.value.topic_title
  } catch (e) {
    error.value = e
  }
}

function edit(m) {
  Object.assign(form, { ...m, prerequisites: m.prerequisites.join(', '), learning_outcomes: [...m.learning_outcomes] })
}

async function save() {
  error.value = null
  saved.value = ''
  const body = {
    course_code: form.course_code,
    course_title: form.course_title,
    credit_units: Number(form.credit_units),
    prerequisites: form.prerequisites.split(',').map((p) => p.trim()).filter(Boolean),
    learning_outcomes: form.learning_outcomes.map((o) => o.trim()).filter(Boolean),
  }
  try {
    const { mapping } = form.map_id
      ? await api.put(`/mappings/${form.map_id}`, body)
      : await api.post(`/recommendations/${props.id}/mapping`, body)
    saved.value = `Saved ${mapping.course_code}.`
    reset()
    await load()
  } catch (e) {
    error.value = e
  }
}

async function remove(m) {
  if (!window.confirm(`Remove ${m.course_code}?`)) return
  try {
    await api.delete(`/mappings/${m.map_id}`)
    await load()
  } catch (e) {
    error.value = e
  }
}

onMounted(load)
</script>

<template>
  <template v-if="rec">
    <nav class="small mb-2"><RouterLink :to="`/recommendations/${id}`">{{ rec.topic_title }}</RouterLink> / Curriculum mapping</nav>
    <h1 class="h3 mb-3">Curriculum mapping</h1>
  </template>
  <ErrorAlert :error="error" />
  <div v-if="saved" class="alert alert-success py-2" data-test="mapping-saved">{{ saved }}</div>
  <div class="row g-3">
    <div class="col-lg-7">
      <form class="card card-body" data-test="mapping-form" @submit.prevent="save">
        <h2 class="h6">{{ form.map_id ? `Edit ${form.course_code}` : 'Propose a course' }}</h2>
        <div class="row g-2">
          <div class="col-sm-4">
            <label class="form-label small" for="code">Course code</label>
            <input id="code" v-model="form.course_code" class="form-control" placeholder="CSC 413" required />
          </div>
          <div class="col-sm-8">
            <label class="form-label small" for="ctitle">Course title</label>
            <input id="ctitle" v-model="form.course_title" class="form-control" maxlength="255" required />
          </div>
          <div class="col-sm-4">
            <label class="form-label small" for="units">Credit units</label>
            <select id="units" v-model.number="form.credit_units" class="form-select">
              <option :value="1">1</option><option :value="2">2</option><option :value="3">3</option>
            </select>
          </div>
          <div class="col-sm-8">
            <label class="form-label small" for="prereq">Prerequisites (comma-separated codes)</label>
            <input id="prereq" v-model="form.prerequisites" class="form-control" placeholder="CSC 201, CSC 301" />
          </div>
        </div>
        <label class="form-label small mt-3">Learning outcomes</label>
        <div v-for="(o, i) in form.learning_outcomes" :key="i" class="input-group input-group-sm mb-1">
          <span class="input-group-text">{{ i + 1 }}</span>
          <input v-model="form.learning_outcomes[i]" class="form-control" :aria-label="`Learning outcome ${i + 1}`" placeholder="Students will be able to…" />
          <button v-if="form.learning_outcomes.length > 1" type="button" class="btn btn-outline-secondary" @click="form.learning_outcomes.splice(i, 1)">Remove</button>
        </div>
        <button type="button" class="btn btn-link btn-sm px-0 align-self-start" @click="form.learning_outcomes.push('')">Add outcome</button>
        <div class="d-flex gap-2 mt-2">
          <button class="btn btn-primary" type="submit">{{ form.map_id ? 'Save changes' : 'Add course' }}</button>
          <button v-if="form.map_id" type="button" class="btn btn-outline-secondary" @click="reset">Cancel</button>
        </div>
      </form>
    </div>
    <div class="col-lg-5">
      <div class="card card-body">
        <h2 class="h6">Proposed courses for this recommendation</h2>
        <div v-for="m in mappings" :key="m.map_id" class="border-top pt-2 mt-2 small">
          <div class="d-flex justify-content-between">
            <strong>{{ m.course_code }}: {{ m.course_title }}</strong>
            <span class="text-nowrap">
              <button class="btn btn-sm btn-link p-0 me-2" @click="edit(m)">Edit</button>
              <button class="btn btn-sm btn-link p-0 text-danger" @click="remove(m)">Remove</button>
            </span>
          </div>
          <div>{{ m.credit_units }} units · Prerequisites: {{ m.prerequisites.join(', ') || 'none' }}</div>
          <ol class="mb-0 ps-3"><li v-for="(o, i) in m.learning_outcomes" :key="i">{{ o }}</li></ol>
        </div>
        <div v-if="!mappings.length" class="small text-body-secondary">None yet.</div>
      </div>
    </div>
  </div>
</template>
