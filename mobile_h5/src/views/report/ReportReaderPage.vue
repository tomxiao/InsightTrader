<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { showToast } from 'vant'

import { reportsApi } from '@api/reports'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import ReportEntryCard from '@components/report/ReportEntryCard.vue'
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
        <div class="report-page__header-main">
          <strong>完整报告</strong>
          <span class="mobile-subtle">沉浸阅读</span>
        </div>
        <span />
      </div>
    </template>

    <div class="report-page">
      <van-skeleton v-if="loading" title :row="8" />
      <template v-else-if="report">
        <ReportEntryCard
          :title="report.title || `${report.stockSymbol} 分析报告`"
          :description="`标的：${report.stockSymbol}`"
        >
          <div v-if="report.executiveSummary" class="report-page__summary">
            <h3>核心摘要</h3>
            <p>{{ report.executiveSummary }}</p>
          </div>
        </ReportEntryCard>

        <section class="mobile-card report-page__markdown">
          <div class="report-page__markdown-head">
            <strong>全文</strong>
            <span class="mobile-subtle">向下滚动阅读完整分析</span>
          </div>
          <div v-html="htmlContent" />
        </section>
      </template>
      <ReportEntryCard
        v-else
        title="报告暂不可用"
        description="当前没有可展示的报告内容，请返回会话页重新打开相关分析。"
      />
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--mobile-space-md);
}

.report-page__header-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.report-page__summary h3,
.report-page__summary p {
  margin: 0;
}

.report-page__summary {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-page__markdown-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 18px;
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
</style>
