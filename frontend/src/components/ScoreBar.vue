<script setup>
import { score } from '../utils/format'

defineProps({ label: { type: String, required: true }, value: { type: Number, default: null } })
</script>

<template>
  <div class="mb-1">
    <div class="d-flex justify-content-between small">
      <span class="text-body-secondary">{{ label }}</span>
      <span class="fw-semibold">{{ score(value) }}</span>
    </div>
    <div class="score-bar" role="progressbar" :aria-label="label" :aria-valuenow="value" aria-valuemin="0" aria-valuemax="1">
      <div :style="{ width: `${Math.max(0, Math.min(1, value || 0)) * 100}%` }"></div>
    </div>
  </div>
</template>
