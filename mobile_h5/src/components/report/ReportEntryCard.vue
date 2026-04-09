<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description?: string
    actionLabel?: string
    compact?: boolean
  }>(),
  {
    description: '',
    actionLabel: '',
    compact: false
  }
)
</script>

<template>
  <section class="mobile-card" :class="{ 'mobile-card--compact': compact }">
    <h2 class="card-title">{{ title }}</h2>
    <p v-if="description" class="card-description">{{ description }}</p>
    <slot />
    <div v-if="actionLabel || $slots.action" class="card-action">
      <slot name="action">
        <span class="card-action__label">{{ actionLabel }}</span>
      </slot>
    </div>
  </section>
</template>

<style scoped>
.mobile-card--compact {
  padding: var(--mobile-space-md);
}

.card-title {
  margin: 0 0 8px;
  font-size: 18px;
  line-height: 1.35;
}

.card-description {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}

.card-action {
  margin-top: 16px;
}

.card-action__label {
  color: var(--mobile-color-primary);
  font-weight: 600;
}
</style>
