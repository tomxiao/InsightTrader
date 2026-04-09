import { request } from './request'

export const reportsApi = {
  getReportDetail(id: string) {
    return request.get(`/reports/${id}/detail`)
  }
}
