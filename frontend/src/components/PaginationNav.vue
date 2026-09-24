<script setup>
defineProps({ pagination: { type: Object, default: null } })
defineEmits(['change'])
</script>

<template>
  <nav v-if="pagination && pagination.pages > 1" class="d-flex align-items-center gap-2 mt-2" aria-label="Pagination">
    <button class="btn btn-sm btn-outline-secondary" :disabled="pagination.page <= 1" @click="$emit('change', pagination.page - 1)">
      Previous
    </button>
    <span class="small text-body-secondary">Page {{ pagination.page }} of {{ pagination.pages }} · {{ pagination.total }} items</span>
    <button
      class="btn btn-sm btn-outline-secondary"
      :disabled="pagination.page >= pagination.pages"
      @click="$emit('change', pagination.page + 1)"
    >
      Next
    </button>
  </nav>
</template>
