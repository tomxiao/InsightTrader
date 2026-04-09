export interface ReportSummary {
  id: string
  stockSymbol: string
  title?: string
  summary?: string
}

export interface ReportDetail extends ReportSummary {
  executiveSummary?: string
  contentMarkdown?: string
}
