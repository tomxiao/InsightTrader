<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <section class="mobile-card">
    <h1 class="mobile-title">{{ title }}</h1>
    <p class="mobile-description">{{ description }}</p>
  </section>
</template>
