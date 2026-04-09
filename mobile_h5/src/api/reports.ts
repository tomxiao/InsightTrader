import type { ReportDetail } from '@/types/report'
import { request } from './request'

export const reportsApi = {
  getReportDetail(id: string) {
    return request.get<ReportDetail>(`/reports/${id}/detail`).then(response => response.data)
  }
}
