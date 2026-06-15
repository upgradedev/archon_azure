import { useState, useEffect, useMemo } from 'react'
import {
  Layout, Typography, Upload as AntUpload, Button,
  Steps, Card, Space, Alert, Tag, theme, Progress, Tooltip,
  Table, Select, Checkbox, Spin,
} from 'antd'
import {
  InboxOutlined, RocketOutlined, CheckCircleOutlined,
  EditOutlined, CalendarOutlined, WarningOutlined, CheckOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd'
import { api } from '../api/client'
import JobStatus from '../components/JobStatus'
import type { ExtractedDoc, DocType, CompanyProfile } from '../types/financial'

const { Content } = Layout
const { Title, Text } = Typography
const { Dragger } = AntUpload
const { useToken } = theme

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff,.tif,.webp'
const MONTH_NAMES = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december',
]

const DOC_TYPE_OPTIONS: { value: DocType; label: string }[] = [
  { value: 'sales',            label: 'Sales Invoice' },
  { value: 'invoice',          label: 'Purchase Invoice' },
  { value: 'expense',          label: 'Expense' },
  { value: 'payroll_register', label: 'Payroll Register' },
  { value: 'payslip',          label: 'Payslip' },
  { value: 'payroll',          label: 'Payroll' },
  { value: 'bank_confirmation',label: 'Bank Statement' },
  { value: 'account_statement',label: 'Account Statement' },
  { value: 'unknown',          label: 'Unknown' },
]

type MatchStatus = 'matched' | 'unrelated' | 'unconfigured'

interface ReviewRow extends ExtractedDoc {
  _key: string
  _include: boolean
  _docType: DocType
  _status: MatchStatus
}

function matchStatus(doc: ExtractedDoc, profile: CompanyProfile): MatchStatus {
  const normName = (profile.company_name || '').trim().toLowerCase()
  const normTax  = (profile.company_tax_id || '').replace(/\D/g, '')
  if (!normName && !normTax) return 'unconfigured'
  const vendorTax = (doc.vendor_tax_id || '').replace(/\D/g, '')
  if (normTax && vendorTax === normTax) return 'matched'
  if (normName && (doc.vendor_name  || '').toLowerCase().includes(normName)) return 'matched'
  if (normName && (doc.recipient_name || '').toLowerCase().includes(normName)) return 'matched'
  return 'unrelated'
}

function detectPeriodFromFiles(files: UploadFile[]): string {
  for (const file of files) {
    const name = (file.name || '').toLowerCase()
    const m = name.match(/(\d{4})[-_](0[1-9]|1[0-2])/)
    if (m) return `${m[1]}-${m[2]}`
    for (let i = 0; i < MONTH_NAMES.length; i++) {
      if (name.includes(MONTH_NAMES[i])) {
        const ym = name.match(/(\d{4})/)
        if (ym) {
          const year = Number(ym[1])
          // Sanity check: only accept years in the plausible range
          if (year >= 2020 && year <= new Date().getFullYear() + 1) {
            return `${ym[1]}-${String(i + 1).padStart(2, '0')}`
          }
        }
      }
    }
  }
  const d = new Date()
  d.setMonth(d.getMonth() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function fmtPeriod(p: string) {
  const [y, m] = p.split('-')
  return new Date(Number(y), Number(m) - 1).toLocaleString('en-GB', { month: 'long', year: 'numeric' })
}

interface UploadPageProps {
  onComplete?: (period: string) => void
}

export default function UploadPage({ onComplete }: UploadPageProps = {}) {
  const { token } = useToken()
  const [fileList, setFileList]           = useState<UploadFile[]>([])
  const [detectedPeriod, setDetectedPeriod] = useState<string>('')
  const [editingPeriod, setEditingPeriod] = useState(false)
  const [step, setStep]                   = useState(0)
  const [jobId, setJobId]                 = useState<string | null>(null)
  const [error, setError]                 = useState<string | null>(null)
  const [submitting, setSubmitting]       = useState(false)
  const [uploadPct, setUploadPct]         = useState(0)

  // Review step state
  const [reviewRows, setReviewRows]       = useState<ReviewRow[]>([])
  const [companyProfile, setCompanyProfile] = useState<CompanyProfile | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [confirming, setConfirming]       = useState(false)

  // Analysis step state
  const [analyzing, setAnalyzing]         = useState(false)
  const [analyzeError, setAnalyzeError]   = useState<string | null>(null)

  useEffect(() => {
    if (fileList.length > 0) setDetectedPeriod(detectPeriodFromFiles(fileList))
  }, [fileList])

  // Last 24 months for the period Select, capped at current month
  const PERIOD_OPTIONS = useMemo(() => {
    const now = new Date()
    return Array.from({ length: 24 }, (_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      return { value: val, label: fmtPeriod(val) }
    })
  }, [])

  const handleSubmit = async () => {
    if (!detectedPeriod || fileList.length === 0) return
    setError(null)
    setSubmitting(true)
    setUploadPct(0)
    try {
      const files     = fileList.map(f => f.originFileObj as File)
      const fileNames = fileList.map(f => f.name)
      const { uploadId } = await api.upload(files, detectedPeriod, setUploadPct, fileNames)
      const job = await api.submitJob(uploadId, detectedPeriod)
      setJobId(job.id)
      setStep(1)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleJobComplete = async () => {
    setStep(2)
    setReviewLoading(true)
    try {
      const [docsResp, profile] = await Promise.all([
        api.getDocuments(detectedPeriod),
        api.getCompanyProfile(),
      ])
      setCompanyProfile(profile)
      const rows: ReviewRow[] = docsResp.documents.map((doc, i) => ({
        ...doc,
        _key: `${i}::${doc.source_file}`,
        _include: true,
        _docType: doc.doc_type,
        _status: matchStatus(doc, profile),
      }))
      setReviewRows(rows)
    } catch {
      // If review fetch fails, skip straight to analysis
      runAnalysis()
    } finally {
      setReviewLoading(false)
    }
  }

  const updateRow = (key: string, patch: Partial<ReviewRow>) =>
    setReviewRows(prev => prev.map(r => r._key === key ? { ...r, ...patch } : r))

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      const approved = reviewRows
        .filter(r => r._include)
        .map(r => ({ ...r, doc_type: r._docType } as ExtractedDoc))

      const hasChanges = reviewRows.some(r => !r._include || r._docType !== r.doc_type)
      if (hasChanges) {
        await api.updateDocuments(detectedPeriod, approved)
      }
    } catch {
      // Proceed regardless — analysis will use original extraction
    } finally {
      setConfirming(false)
      runAnalysis()
    }
  }

  const runAnalysis = async () => {
    setStep(3)
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      await api.analyze(detectedPeriod)
      setStep(4)
      setTimeout(() => onComplete?.(detectedPeriod), 1200)
    } catch (err: unknown) {
      setAnalyzeError(err instanceof Error ? err.message : 'Analysis failed')
      setAnalyzing(false)
    }
  }

  const unrelated = reviewRows.filter(r => r._status === 'unrelated')
  const included  = reviewRows.filter(r => r._include)

  const REVIEW_COLUMNS = [
    {
      title: '',
      key: 'include',
      width: 36,
      render: (_: unknown, row: ReviewRow) => (
        <Checkbox
          checked={row._include}
          onChange={e => updateRow(row._key, { _include: e.target.checked })}
        />
      ),
    },
    {
      title: 'File',
      key: 'file',
      ellipsis: true,
      render: (_: unknown, row: ReviewRow) => (
        <Tooltip title={row.source_file.split('/').pop()}>
          <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>
            {row.source_file.split('/').pop()}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      width: 170,
      render: (_: unknown, row: ReviewRow) => (
        <Select<DocType>
          size="small"
          value={row._docType}
          onChange={v => updateRow(row._key, { _docType: v })}
          options={DOC_TYPE_OPTIONS}
          style={{ width: '100%' }}
          onClick={e => e.stopPropagation()}
        />
      ),
    },
    {
      title: 'Sender / Recipient',
      key: 'party',
      ellipsis: true,
      render: (_: unknown, row: ReviewRow) => {
        const sender    = row.vendor_name
        const recipient = row.recipient_name
        return (
          <Space direction="vertical" size={0} style={{ gap: 0 }}>
            {sender    && <Text style={{ fontSize: 11 }}>↑ {sender}</Text>}
            {recipient && <Text style={{ fontSize: 11 }} type="secondary">↓ {recipient}</Text>}
            {!sender && !recipient && <Text type="secondary">—</Text>}
          </Space>
        )
      },
    },
    {
      title: 'Match',
      key: 'status',
      width: 90,
      render: (_: unknown, row: ReviewRow) => {
        if (row._status === 'matched')
          return <Tag color="green" icon={<CheckOutlined />} style={{ fontSize: 10 }}>Matched</Tag>
        if (row._status === 'unrelated')
          return <Tag color="orange" icon={<WarningOutlined />} style={{ fontSize: 10 }}>Review</Tag>
        return <Tag color="default" style={{ fontSize: 10 }}>—</Tag>
      },
    },
  ]

  const inner = (
    <Space direction="vertical" size={24} style={{ width: '100%' }}>
      {!onComplete && (
        <div>
          <Title level={2} style={{ margin: 0 }}>Archon</Title>
          <Text type="secondary">Agentic Financial Intelligence — upload documents, get P&L insights</Text>
        </div>
      )}

      <Steps
        current={step}
        items={[
          { title: 'Select' },
          { title: 'Extract' },
          { title: 'Review' },
          { title: 'Analyse' },
          { title: 'Ready', icon: step === 4 ? <CheckCircleOutlined /> : undefined },
        ]}
      />

      {/* ── Step 0: file selection ──────────────────────────────────── */}
      {step === 0 && (
        <Card>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <div>
              <Text strong>Documents</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                Invoices · Payroll · Expenses · Sales — any language
              </Text>
              <Dragger
                multiple
                accept={ACCEPTED_TYPES}
                fileList={fileList}
                beforeUpload={() => false}
                onChange={({ fileList: fl }) => setFileList(fl)}
                style={{ marginTop: 8 }}
              >
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">Drop files here or click to browse</p>
                <p className="ant-upload-hint">PDF · DOCX · JPG · PNG · TIFF — scanned or digital, Greek or English</p>
              </Dragger>
            </div>

            {fileList.length > 0 && (
              <Space wrap>
                {fileList.map(f => <Tag key={f.uid} color="blue">{f.name}</Tag>)}
              </Space>
            )}

            {fileList.length > 0 && detectedPeriod && (
              <div style={{
                background: token.colorFillAlter,
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: token.borderRadius,
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                flexWrap: 'wrap',
              }}>
                <CalendarOutlined style={{ color: '#6366f1' }} />
                {editingPeriod ? (
                  <Select
                    size="small"
                    defaultValue={detectedPeriod}
                    options={PERIOD_OPTIONS}
                    onChange={(v: string) => { setDetectedPeriod(v); setEditingPeriod(false) }}
                    onBlur={() => setEditingPeriod(false)}
                    style={{ minWidth: 160 }}
                    autoFocus
                    open
                  />
                ) : (
                  <>
                    <Tooltip title="Each document's own date (issue_date) takes priority. This period is used only for documents where no date is detected.">
                      <Text>
                        Fallback period: <strong>{fmtPeriod(detectedPeriod)}</strong>
                      </Text>
                    </Tooltip>
                    <Tooltip title="Change fallback period">
                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setEditingPeriod(true)}
                      />
                    </Tooltip>
                  </>
                )}
              </div>
            )}

            {submitting && (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Uploading {fileList.length} file{fileList.length !== 1 ? 's' : ''}…
                </Text>
                <Progress
                  percent={uploadPct}
                  size="small"
                  status="active"
                  style={{ marginTop: 4 }}
                  format={pct => `${Math.round(((pct ?? 0) / 100) * fileList.length)} / ${fileList.length}`}
                />
              </div>
            )}

            {error && <Alert type="error" message={error} showIcon />}

            <Button
              type="primary"
              size="large"
              icon={<RocketOutlined />}
              block
              loading={submitting}
              disabled={!detectedPeriod || fileList.length === 0 || editingPeriod}
              onClick={handleSubmit}
            >
              {submitting ? 'Uploading…' : 'Extract & Analyze'}
            </Button>
          </Space>
        </Card>
      )}

      {/* ── Step 1: extraction running ──────────────────────────────── */}
      {step === 1 && jobId && (
        <JobStatus jobId={jobId} onComplete={handleJobComplete} />
      )}

      {/* ── Step 2: document review ─────────────────────────────────── */}
      {step === 2 && (
        <Card
          title="Review extracted documents"
          loading={reviewLoading}
        >
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {!reviewLoading && (
              <>
                {companyProfile && !companyProfile.company_name && !companyProfile.company_tax_id && (
                  <Alert
                    type="warning"
                    showIcon
                    message="Company profile not configured"
                    description="Set COMPANY_NAME and COMPANY_TAX_ID on the analysis service to enable automatic document matching."
                  />
                )}

                {unrelated.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    icon={<WarningOutlined />}
                    message={`${unrelated.length} document${unrelated.length !== 1 ? 's' : ''} may not belong to ${companyProfile?.company_name || 'your company'}`}
                    description="Review the highlighted rows. Uncheck any document you want to exclude from analysis."
                  />
                )}

                <Table<ReviewRow>
                  size="small"
                  pagination={false}
                  columns={REVIEW_COLUMNS}
                  dataSource={reviewRows}
                  rowKey={r => r._key}
                  rowClassName={r => r._status === 'unrelated' && r._include ? 'row-warn' : ''}
                  scroll={{ x: 560 }}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {included.length} of {reviewRows.length} documents will be analysed
                  </Text>
                  <Button
                    type="primary"
                    loading={confirming}
                    disabled={included.length === 0}
                    onClick={handleConfirm}
                    icon={<ThunderboltOutlined />}
                  >
                    Confirm & Run Analysis
                  </Button>
                </div>
              </>
            )}
          </Space>
        </Card>
      )}

      {/* ── Step 3: analysis running ─────────────────────────────────── */}
      {step === 3 && (
        <Card>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {analyzing && (
              <>
                <Space>
                  <Spin />
                  <Text strong>Running 7-agent analysis pipeline…</Text>
                </Space>
                <Progress percent={70} status="active" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Classifier → P&L → Cash Flow → Employee → Validator → Reconciliation → Narrator
                </Text>
              </>
            )}
            {analyzeError && (
              <>
                <Alert type="error" message={`Analysis failed: ${analyzeError}`} showIcon />
                <Button type="primary" onClick={runAnalysis}>Retry</Button>
              </>
            )}
          </Space>
        </Card>
      )}

      {/* ── Step 4: done ────────────────────────────────────────────── */}
      {step === 4 && (
        <Alert
          type="success"
          message="Analysis complete — returning to dashboard…"
          showIcon
        />
      )}
    </Space>
  )

  if (onComplete) {
    return <div style={{ padding: 24 }}>{inner}</div>
  }

  return (
    <Layout style={{ minHeight: '100vh', background: token.colorBgLayout }}>
      <Content style={{ maxWidth: 800, margin: '0 auto', padding: '48px 24px' }}>
        {inner}
      </Content>
    </Layout>
  )
}
