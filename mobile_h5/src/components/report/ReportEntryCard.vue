<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <section class="mobile-card">
    <h2 class="card-title">{{ title }}</h2>
    <p class="card-description">{{ description }}</p>
  </section>
</template>

<style scoped>
.card-title {
  margin: 0 0 8px;
  font-size: 18px;
}

.card-description {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}
</style>
