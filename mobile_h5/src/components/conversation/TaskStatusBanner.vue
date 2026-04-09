<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    detail?: string
  }>(),
  {
    title: '任务状态',
    detail: '后续将在此展示运行中步骤、耗时和剩余时间。'
  }
)
</script>

<template>
  <div class="status-banner">
    <strong>{{ title }}</strong>
    <p>{{ detail }}</p>
  </div>
</template>

<style scoped>
.status-banner {
  padding: 14px 16px;
  background: rgba(22, 119, 255, 0.08);
  border-radius: var(--mobile-radius-md);
  color: var(--mobile-color-primary);
}

.status-banner strong,
.status-banner p {
  margin: 0;
}

.status-banner p {
  margin-top: 6px;
  line-height: 1.5;
}
</style>
