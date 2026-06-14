import { useState, useEffect } from 'react'
import {
  Layout, Typography, Upload as AntUpload, Button, DatePicker,
  Steps, Card, Space, Alert, Tag, theme, Progress, Tooltip,
} from 'antd'
import { InboxOutlined, RocketOutlined, CheckCircleOutlined, EditOutlined, CalendarOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import dayjs from 'dayjs'
import { api } from '../api/client'
import JobStatus from '../components/JobStatus'

const { Content } = Layout
const { Title, Text } = Typography
const { Dragger } = AntUpload
const { useToken } = theme

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff,.tif,.webp'
const MONTH_NAMES = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december',
]

function detectPeriodFromFiles(files: UploadFile[]): string {
  for (const file of files) {
    const name = (file.name || '').toLowerCase()
    const m = name.match(/(\d{4})[-_](0[1-9]|1[0-2])/)
    if (m) return `${m[1]}-${m[2]}`
    for (let i = 0; i < MONTH_NAMES.length; i++) {
      if (name.includes(MONTH_NAMES[i])) {
        const ym = name.match(/(\d{4})/)
        if (ym) return `${ym[1]}-${String(i + 1).padStart(2, '0')}`
      }
    }
  }
  // Default: previous month
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
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [detectedPeriod, setDetectedPeriod] = useState<string>('')
  const [editingPeriod, setEditingPeriod] = useState(false)
  const [step, setStep] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [uploadPct, setUploadPct] = useState(0)

  // Auto-detect period whenever file list changes
  useEffect(() => {
    if (fileList.length > 0) {
      setDetectedPeriod(detectPeriodFromFiles(fileList))
    }
  }, [fileList])

  const handleSubmit = async () => {
    if (!detectedPeriod || fileList.length === 0) return
    setError(null)
    setSubmitting(true)
    setUploadPct(0)
    try {
      const files = fileList.map(f => f.originFileObj as File)
      const { uploadId } = await api.upload(files, detectedPeriod, setUploadPct)
      const job = await api.submitJob(uploadId, detectedPeriod)
      setJobId(job.id)
      setStep(1)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleJobComplete = () => {
    setStep(2)
    setTimeout(() => onComplete?.(detectedPeriod), 1500)
  }

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
          { title: 'Select documents' },
          { title: 'Extracting data' },
          { title: 'Ready', icon: step === 2 ? <CheckCircleOutlined /> : undefined },
        ]}
      />

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

            {/* Detected period — shown after files are dropped */}
            {fileList.length > 0 && detectedPeriod && (
              <div style={{
                background: token.colorFillAlter,
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: token.borderRadius,
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
              }}>
                <CalendarOutlined style={{ color: '#6366f1' }} />
                {editingPeriod ? (
                  <DatePicker
                    picker="month"
                    defaultValue={dayjs(detectedPeriod)}
                    onChange={(_, s) => {
                      setDetectedPeriod(s as string)
                      setEditingPeriod(false)
                    }}
                    onBlur={() => setEditingPeriod(false)}
                    autoFocus
                    disabledDate={d => d.isAfter(dayjs())}
                  />
                ) : (
                  <>
                    <Text>
                      Detected period: <strong>{fmtPeriod(detectedPeriod)}</strong>
                    </Text>
                    <Tooltip title="Change period">
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

      {step === 1 && jobId && (
        <JobStatus jobId={jobId} onComplete={handleJobComplete} />
      )}

      {step === 2 && (
        <Alert
          type="success"
          message="Extraction complete — returning to dashboard…"
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
