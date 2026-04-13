<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { showToast } from 'vant'

import { reportsApi } from '@api/reports'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import type { ReportDetail } from '@/types/report'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const report = ref<ReportDetail | null>(null)

const htmlContent = computed(
  () => marked.parse(report.value?.contentMarkdown || '', { async: false }) as string
)


const loadReport = async () => {
  const reportId = String(route.params.id || '')
  if (!reportId) return

  loading.value = true
  try {
    report.value = await reportsApi.getReportDetail(reportId)
  } catch (error) {
    showToast((error as Error).message || '加载报告失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadReport)
</script>

<template>
  <MobilePageLayout title="完整报告">
    <template #header>
      <div class="report-page__header">
        <van-button plain size="small" @click="router.back()">返回</van-button>
        <strong class="report-page__header-title">完整报告</strong>
        <span />
      </div>
    </template>

    <div class="report-page">
      <van-skeleton v-if="loading" title :row="8" />
      <template v-else-if="report">
        <section class="mobile-card report-page__markdown">
          <div v-html="htmlContent" />
        </section>
      </template>
      <div v-else class="report-page__empty">
        <p>报告暂不可用</p>
        <p class="mobile-subtle">当前没有可展示的报告内容，请返回会话页重新打开相关分析。</p>
      </div>
    </div>
  </MobilePageLayout>
</template>

<style scoped>
.report-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-page__header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--mobile-space-md);
}

.report-page__header-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 16px;
  pointer-events: none;
}


.report-page__markdown {
  line-height: 1.8;
}

.report-page__markdown :deep(h1),
.report-page__markdown :deep(h2),
.report-page__markdown :deep(h3) {
  margin-top: 1.4em;
  margin-bottom: 0.6em;
}

.report-page__markdown :deep(p) {
  margin: 0 0 1em;
}

.report-page__markdown :deep(ul),
.report-page__markdown :deep(ol) {
  padding-left: 20px;
  color: var(--mobile-color-text-secondary);
}

.report-page__markdown :deep(strong) {
  color: var(--mobile-color-text);
}

.report-page__empty {
  padding: var(--mobile-space-lg);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-page__empty p {
  margin: 0;
}
</style>
