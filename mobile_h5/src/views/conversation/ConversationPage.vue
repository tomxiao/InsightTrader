<template>
  <MobilePageLayout>
    <TaskStatusBanner />
    <div style="height: 16px" />
    <PlaceholderCard
      title="当前会话页"
      description="用于承载会话线程、任务状态、执行摘要卡片和完整报告卡片。"
    />
  </MobilePageLayout>
</template>

<script setup lang="ts">
import PlaceholderCard from '@components/common/PlaceholderCard.vue'
import TaskStatusBanner from '@components/conversation/TaskStatusBanner.vue'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
</script>
