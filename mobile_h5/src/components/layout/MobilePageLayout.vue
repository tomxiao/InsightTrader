<script setup lang="ts">
defineProps<{
  title?: string
  withContentPadding?: boolean
}>()
</script>

<template>
  <div class="mobile-page">
    <header v-if="$slots.header || title" class="mobile-page__header">
      <div class="mobile-page__shell mobile-page__shell--header">
        <slot name="header">
          <div class="mobile-page__header-title">{{ title }}</div>
        </slot>
      </div>
    </header>
    <section v-if="$slots.banner" class="mobile-page__banner">
      <div class="mobile-page__shell">
        <slot name="banner" />
      </div>
    </section>
    <main
      class="mobile-page__content"
      :class="{ 'mobile-page__content--flush': withContentPadding === false }"
    >
      <div class="mobile-page__shell" :class="{ 'mobile-page__shell--flush': withContentPadding === false }">
        <slot />
      </div>
    </main>
    <footer v-if="$slots.footer" class="mobile-page__footer">
      <div class="mobile-page__shell">
        <slot name="footer" />
      </div>
    </footer>
  </div>
</template>

<style scoped>
.mobile-page__shell {
  width: min(100%, 860px);
  margin: 0 auto;
}

.mobile-page__shell--header {
  padding-top: 4px;
}

.mobile-page__shell--flush {
  width: 100%;
  max-width: none;
}
</style>
