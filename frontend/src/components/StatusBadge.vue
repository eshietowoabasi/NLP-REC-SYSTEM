<script setup>
import { statusClass } from '../utils/format'

defineProps({ status: { type: String, default: null }, fallback: { type: String, default: 'Pending review' } })
</script>

<template>
  <span class="badge" :class="statusClass(status || fallback)">{{ status || fallback }}</span>
</template>
