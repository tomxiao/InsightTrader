<template>
  <MobilePageLayout>
    <ReportEntryCard
      title="完整报告阅读层"
      description="用于独立承载长报告阅读，不在会话线程中直接展开完整正文。"
    />
  </MobilePageLayout>
</template>

<script setup lang="ts">
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import ReportEntryCard from '@components/report/ReportEntryCard.vue'
</script>
