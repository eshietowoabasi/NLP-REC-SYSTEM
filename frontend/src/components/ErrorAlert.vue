<script setup>
import { computed } from 'vue'
import { describeError } from '../services/api'

const props = defineProps({ error: { type: [Object, String], default: null } })
const message = computed(() => (typeof props.error === 'string' ? props.error : describeError(props.error)))
</script>

<template>
  <div v-if="error" class="alert alert-danger" role="alert">{{ message }}</div>
</template>
