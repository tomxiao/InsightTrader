<script setup lang="ts">
import { computed } from 'vue'
import { formatSeconds } from '@utils/format'

const props = withDefaults(
  defineProps<{
  status?: 'pending' | 'running' | 'completed' | 'failed' | 'idle'
  title?: string
  detail?: string
  elapsedTime?: number
  remainingTime?: number
  }>(),
  {
    status: 'idle',
    title: '任务状态',
    detail: '后续将在此展示运行中步骤、耗时和剩余时间。',
    elapsedTime: 0,
    remainingTime: 0
  }
)

const statusLabelMap = {
  idle: '待命',
  pending: '准备中',
  running: '运行中',
  completed: '已完成',
  failed: '失败'
} as const

const metrics = computed(() => [
  {
    label: '已用',
    value: formatSeconds(props.elapsedTime ?? 0)
  },
  {
    label: '预计剩余',
    value: formatSeconds(props.remainingTime ?? 0)
  }
])
</script>

<template>
  <div class="status-banner" :data-status="status">
    <div class="status-banner__top">
      <div class="status-banner__copy">
        <strong>{{ title }}</strong>
        <p>{{ detail }}</p>
      </div>
      <span class="status-banner__badge">{{ statusLabelMap[status ?? 'idle'] }}</span>
    </div>
    <div class="status-banner__metrics">
      <div v-for="metric in metrics" :key="metric.label" class="status-banner__metric">
        <span class="status-banner__metric-label">{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-banner {
  padding: 16px 18px;
  background: rgba(93, 139, 255, 0.08);
  border: 1px solid rgba(93, 139, 255, 0.18);
  border-radius: calc(var(--mobile-radius-md) + 2px);
  color: var(--mobile-color-text);
}

.status-banner[data-status='completed'] {
  background: rgba(40, 199, 111, 0.08);
  border-color: rgba(40, 199, 111, 0.24);
}

.status-banner[data-status='failed'] {
  background: rgba(255, 107, 107, 0.08);
  border-color: rgba(255, 107, 107, 0.24);
}

.status-banner__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.status-banner__copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-banner__badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: var(--mobile-color-text-secondary);
  white-space: nowrap;
}

.status-banner strong,
.status-banner p {
  margin: 0;
}

.status-banner strong {
  font-size: 15px;
}

.status-banner p {
  line-height: 1.5;
  color: var(--mobile-color-text-secondary);
}

.status-banner__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.status-banner__metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
}

.status-banner__metric-label {
  font-size: 12px;
  color: var(--mobile-color-text-tertiary);
}
</style>
