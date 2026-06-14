export type DocType = 'invoice' | 'payroll' | 'expense' | 'sales' | 'payroll_register' | 'payslip' | 'bank_confirmation' | 'account_statement' | 'unknown'

export interface ExtractedDoc {
  source_file: string
  doc_type: DocType
  detected_language: string
  issue_date: string | null
  vendor_name: string | null
  vendor_tax_id: string | null
  recipient_name: string | null
  currency: string
  total_amount: number
  subtotal: number | null
  vat_amount: number | null
  vat_rate_pct: number | null
  payment_due_date: string | null
  invoice_number: string | null
  notes: string | null
  confidence: number
  employee_count: number | null
  gross_pay_total: number | null
  net_pay_total: number | null
  employee_name: string | null
  statement_balance: number | null
}

export interface CompanyProfile {
  company_name: string
  company_tax_id: string
}

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface UploadedFile {
  id: string
  filename: string
  sizeBytes: number
  uploadedAt: string
}

export interface UploadResponse {
  uploadId: string
  files: UploadedFile[]
}

export interface Job {
  id: string
  status: JobStatus
  period: string        // YYYY-MM
  documentsCount: number
  createdAt: string
  completedAt?: string
  errorMessage?: string
  progress?: number     // 0-100
}

export interface MonthlyPnL {
  period: string        // YYYY-MM
  revenue: number
  expenses: number
  netProfit: number
  grossMarginPct: number
  operatingMarginPct: number
}

export interface CashFlow {
  period: string
  operating: number
  investing: number
  financing: number
  net: number
}

export interface ExpenseCategory {
  category: string
  amount: number
  percentage: number
  monthOverMonthPct: number
}

export interface VendorSummary {
  name: string
  totalAmount: number
  invoiceCount: number
  avgDaysToPay: number
}

export interface KeyMetrics {
  revenueGrowthPct: number
  expenseRatioPct: number
  cashBurnRate: number
  invoiceCount: number
  avgInvoiceValue: number
  collectionRatePct: number
}

export interface FinancialReport {
  period: string
  pnl: MonthlyPnL
  cashFlow: CashFlow
  expenseBreakdown: ExpenseCategory[]
  topVendors: VendorSummary[]
  keyMetrics: KeyMetrics
  executiveSummary: string
  generatedAt: string
}

export interface AnalysisResponse {
  jobId: string
  report: FinancialReport
}
