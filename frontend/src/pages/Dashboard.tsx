import { useState, useEffect } from 'react'
import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Layout, Typography, Row, Col, Card, Button, Spin, Select,
  Drawer, Space, Statistic, Tag, Alert, Divider, theme, Tooltip,
  Modal, Table,
} from 'antd'
import {
  UploadOutlined, ThunderboltOutlined, RobotOutlined,
  LinkOutlined, ArrowUpOutlined, ArrowDownOutlined,
  ReloadOutlined, DeleteOutlined, FileTextOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, Legend, ResponsiveContainer,
  ReferenceLine, PieChart, Pie, Cell, AreaChart, Area,
  TooltipProps,
} from 'recharts'
import { api } from '../api/client'
import UploadPage from './Upload'
import type { FinancialReport, ExpenseCategory, ExtractedDoc } from '../types/financial'

const { Content, Header } = Layout
const { Title, Text, Paragraph } = Typography
const { useToken } = theme

const EUR = (v: number) =>
  new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(v)

const fmtPeriod = (p: string) => {
  const [y, m] = p.split('-')
  return new Date(Number(y), Number(m) - 1).toLocaleString('en-GB', { month: 'long', year: 'numeric' })
}

const PIE_COLORS = ['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e']

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a1a2e', border: '1px solid #333', borderRadius: 8,
      padding: '10px 14px', fontSize: 13,
    }}>
      {label && <div style={{ color: '#aaa', marginBottom: 6 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color ?? '#fff', marginBottom: 2 }}>
          {p.name}: <strong style={{ color: '#fff' }}>{EUR(Math.abs(Number(p.value)))}</strong>
        </div>
      ))}
    </div>
  )
}

function PieCustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div style={{
      background: '#1a1a2e', border: '1px solid #333', borderRadius: 8,
      padding: '10px 14px', fontSize: 13,
    }}>
      <div style={{ color: p.payload?.fill ?? '#aaa', marginBottom: 4, fontWeight: 600 }}>{p.name}</div>
      <div style={{ color: '#fff' }}>{EUR(Number(p.value))}</div>
    </div>
  )
}

function parseSummary(raw: string): { body: string; citations: string[] } {
  const marker = '\n\nSources: '
  const idx = raw.indexOf(marker)
  if (idx === -1) return { body: raw, citations: [] }
  return {
    body: raw.slice(0, idx),
    citations: raw.slice(idx + marker.length).split(' · ').filter(Boolean),
  }
}

// Aggregate multiple reports into one combined view
function aggregateReports(reports: FinancialReport[]): FinancialReport {
  if (reports.length === 1) return reports[0]

  const totalRevenue = reports.reduce((s, r) => s + r.pnl.revenue, 0)
  const totalExpenses = reports.reduce((s, r) => s + r.pnl.expenses, 0)
  const totalNetProfit = reports.reduce((s, r) => s + r.pnl.netProfit, 0)
  const grossMarginPct = totalRevenue > 0 ? (totalNetProfit / totalRevenue) * 100 : 0

  // Merge expense categories
  const catMap: Record<string, ExpenseCategory> = {}
  for (const r of reports) {
    for (const e of r.expenseBreakdown) {
      if (catMap[e.category]) {
        catMap[e.category].amount += e.amount
      } else {
        catMap[e.category] = { ...e }
      }
    }
  }
  const mergedExpenses = Object.values(catMap).sort((a, b) => b.amount - a.amount)
  const expTotal = mergedExpenses.reduce((s, e) => s + e.amount, 0)
  mergedExpenses.forEach(e => { e.percentage = expTotal > 0 ? (e.amount / expTotal) * 100 : 0 })

  const sorted = [...reports].sort((a, b) => b.period.localeCompare(a.period))
  const latest = sorted[0]

  return {
    ...latest,
    period: `${sorted[sorted.length - 1].period} – ${sorted[0].period}`,
    pnl: {
      ...latest.pnl,
      revenue: totalRevenue,
      expenses: totalExpenses,
      netProfit: totalNetProfit,
      grossMarginPct,
    },
    cashFlow: {
      ...latest.cashFlow,
      operating: reports.reduce((s, r) => s + r.cashFlow.operating, 0),
      investing: reports.reduce((s, r) => s + r.cashFlow.investing, 0),
      financing: reports.reduce((s, r) => s + r.cashFlow.financing, 0),
      net: reports.reduce((s, r) => s + r.cashFlow.net, 0),
    },
    expenseBreakdown: mergedExpenses,
    keyMetrics: {
      ...latest.keyMetrics,
      invoiceCount: reports.reduce((s, r) => s + r.keyMetrics.invoiceCount, 0),
    },
  }
}

export default function DashboardPage() {
  const { token } = useToken()
  const queryClient = useQueryClient()
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([])
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [activeTile, setActiveTile] = useState<string | null>(null)

  const { data: periodsData, isLoading: periodsLoading } = useQuery<{ periods: string[] }>({
    queryKey: ['periods'],
    queryFn: api.getPeriods,
  })

  const periods = periodsData?.periods ?? []

  useEffect(() => {
    if (selectedPeriods.length === 0 && periods.length > 0) {
      setSelectedPeriods([[...periods].sort().reverse()[0]])
    }
  }, [periods, selectedPeriods])

  // Fetch all selected periods in parallel
  const reportQueries = useQueries({
    queries: selectedPeriods.map(period => ({
      queryKey: ['report', period],
      queryFn: () => api.getReport(period),
      enabled: !!period,
      retry: (count: number, err: unknown) => {
        const status = (err as { response?: { status?: number } })?.response?.status
        return !status || status >= 500 ? count < 2 : false
      },
    })),
  })

  const reportsLoading = reportQueries.some(q => q.isLoading)
  const loadedReports = reportQueries
    .filter(q => q.data?.report)
    .map(q => q.data!.report)
  const missingPeriods = selectedPeriods.filter((_p, i) => {
    const status = (reportQueries[i]?.error as { response?: { status?: number } })?.response?.status
    return status === 404
  })

  const report = loadedReports.length > 0 ? aggregateReports(loadedReports) : null

  const analyzeMutation = useMutation({
    mutationFn: (period: string) => api.analyze(period),
    onSuccess: (_, period) => queryClient.invalidateQueries({ queryKey: ['report', period] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (period: string) => api.deletePeriod(period),
    onSuccess: (_, period) => {
      queryClient.invalidateQueries({ queryKey: ['periods'] })
      queryClient.invalidateQueries({ queryKey: ['report', period] })
      setSelectedPeriods(prev => prev.filter(p => p !== period))
      setDeleteTarget(null)
    },
  })

  const bg = token.colorBgLayout
  const cardBg = token.colorBgContainer
  const border = token.colorBorderSecondary

  // Chart data
  const isMulti = loadedReports.length > 1

  const pnlChartData = isMulti
    ? loadedReports.map(r => ({
        name: fmtPeriod(r.period),
        Revenue: r.pnl.revenue,
        Expenses: r.pnl.expenses,
        'Net Profit': r.pnl.netProfit,
      }))
    : report ? [
        { name: 'Revenue', value: report.pnl.revenue, fill: '#6366f1' },
        { name: 'Expenses', value: report.pnl.expenses, fill: '#f43f5e' },
        { name: 'Net Profit', value: report.pnl.netProfit, fill: '#22c55e' },
      ] : []

  const cashChartData = report ? [
    { name: 'Operating', value: report.cashFlow.operating },
    { name: 'Investing', value: report.cashFlow.investing },
    { name: 'Financing', value: report.cashFlow.financing },
    { name: 'Net', value: report.cashFlow.net },
  ] : []

  const expenseData = report?.expenseBreakdown.map(d => ({ name: d.category, value: d.amount })) ?? []

  const { body: summaryBody, citations } = parseSummary(report?.executiveSummary ?? '')

  // Which doc_types to show per tile
  const TILE_DOC_TYPES: Record<string, string[]> = {
    Revenue:      ['sales'],
    Expenses:     ['invoice', 'expense', 'payroll', 'payroll_register', 'payslip'],
    'Net Profit': ['sales', 'invoice', 'expense', 'payroll', 'payroll_register', 'payslip'],
    'Gross Margin': ['sales'],
    'Cash Net':   ['bank_confirmation'],
    Invoices:     ['sales', 'invoice', 'expense'],
  }

  // Fetch documents for all selected periods when a tile is active
  const docQueries = useQueries({
    queries: (activeTile ? selectedPeriods : []).map(period => ({
      queryKey: ['documents', period],
      queryFn: () => api.getDocuments(period),
      enabled: !!activeTile,
    })),
  })
  const allDocs: (ExtractedDoc & { period: string })[] = docQueries
    .flatMap((q, i) =>
      (q.data?.documents ?? []).map(d => ({ ...d, period: selectedPeriods[i] }))
    )
  const docsLoading = docQueries.some(q => q.isLoading)

  const DOC_COLUMNS = [
    { title: 'File', dataIndex: 'source_file', key: 'source_file',
      render: (v: string) => <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{v.split('/').pop()}</Text> },
    { title: 'Type', dataIndex: 'doc_type', key: 'doc_type',
      render: (v: string) => {
        const color: Record<string, string> = { sales: 'green', invoice: 'orange', expense: 'red', payroll: 'purple', payroll_register: 'purple', payslip: 'purple', bank_confirmation: 'blue', unknown: 'default' }
        return <Tag color={color[v] ?? 'default'} style={{ fontSize: 10 }}>{v}</Tag>
      }},
    { title: 'Invoice #', dataIndex: 'invoice_number', key: 'invoice_number',
      render: (v: string | null) => v ?? <Text type="secondary" style={{ fontSize: 11 }}>—</Text> },
    { title: 'Counterparty', key: 'counterparty',
      render: (_: unknown, d: ExtractedDoc) => d.vendor_name ?? d.recipient_name ?? '—' },
    { title: 'Date', dataIndex: 'issue_date', key: 'issue_date',
      render: (v: string | null) => v
        ? v
        : <Tag color="warning" style={{ fontSize: 10 }}>Not detected</Tag> },
    { title: 'Amount', dataIndex: 'total_amount', key: 'total_amount',
      align: 'right' as const,
      render: (v: number, d: ExtractedDoc) => (
        <span style={{ color: d.doc_type === 'sales' ? '#22c55e' : '#f43f5e' }}>{EUR(v)}</span>
      )},
    { title: 'Confidence', dataIndex: 'confidence', key: 'confidence',
      render: (v: number) => <Text type="secondary" style={{ fontSize: 11 }}>{(v * 100).toFixed(0)}%</Text> },
  ]

  return (
    <Layout style={{ minHeight: '100vh', background: bg }}>
      {/* ── Header ─────────────────────────────────────────── */}
      <Header style={{
        background: cardBg, borderBottom: `1px solid ${border}`,
        padding: '0 24px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', height: 56,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Title level={4} style={{ margin: 0, color: '#6366f1' }}>Archon</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>Financial Intelligence</Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {periodsLoading ? <Spin size="small" /> : (
            <Select
              mode="multiple"
              style={{ minWidth: 220, maxWidth: 400 }}
              placeholder="Select period(s)"
              value={selectedPeriods}
              onChange={setSelectedPeriods}
              maxTagCount="responsive"
              options={[
                { value: '__all__', label: 'All periods' },
                ...[...periods].sort().reverse().map(p => ({ value: p, label: fmtPeriod(p) })),
              ]}
              onSelect={(v: string) => {
                if (v === '__all__') setSelectedPeriods([...periods])
              }}
              onDeselect={(v: string) => {
                if (v === '__all__') setSelectedPeriods([])
              }}
              notFoundContent="No periods available"
            />
          )}
          <Tooltip title="Refresh">
            <Button
              icon={<ReloadOutlined />}
              onClick={() => selectedPeriods.forEach(p =>
                queryClient.invalidateQueries({ queryKey: ['report', p] })
              )}
              disabled={selectedPeriods.length === 0}
            />
          </Tooltip>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadOpen(true)}
          >
            Upload Documents
          </Button>
        </div>
      </Header>

      {/* ── Main content ────────────────────────────────────── */}
      <Content style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>

        {/* No data yet */}
        {!periodsLoading && periods.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: 80 }}>
            <Title level={3} type="secondary">No financial data yet</Title>
            <Text type="secondary">Upload documents to get started.</Text>
            <br /><br />
            <Button type="primary" size="large" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
              Upload Documents
            </Button>
          </div>
        )}

        {/* Loading */}
        {reportsLoading && (
          <div style={{ textAlign: 'center', marginTop: 80 }}>
            <Spin size="large" tip="Loading financial report…" />
          </div>
        )}

        {/* Missing reports for selected periods */}
        {!reportsLoading && missingPeriods.length > 0 && loadedReports.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: 80 }}>
            <Title level={3} type="secondary">
              No report for {missingPeriods.map(fmtPeriod).join(', ')}
            </Title>
            <Text type="secondary">Run the 7-agent analysis pipeline to generate a financial report.</Text>
            <br /><br />
            <Space>
              {missingPeriods.map(p => (
                <Button
                  key={p}
                  type="primary" size="large"
                  icon={<ThunderboltOutlined />}
                  loading={analyzeMutation.isPending}
                  onClick={() => analyzeMutation.mutate(p)}
                >
                  {analyzeMutation.isPending ? 'Running analysis…' : `Run Analysis — ${fmtPeriod(p)}`}
                </Button>
              ))}
            </Space>
            {analyzeMutation.isError && (
              <Alert type="error" message="Analysis failed" style={{ marginTop: 16 }} />
            )}
          </div>
        )}

        {/* Report loaded */}
        {report && (
          <Space direction="vertical" size={24} style={{ width: '100%' }}>

            {/* Period label + delete */}
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
                <Title level={3} style={{ margin: 0 }}>
                  {isMulti ? `${selectedPeriods.length} periods combined` : fmtPeriod(report.period)}
                </Title>
                {!isMulti && report.generatedAt && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Generated {new Date(report.generatedAt).toLocaleString('en-GB', {
                      day: '2-digit', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </Text>
                )}
              </div>
              {!isMulti && (
                <Tooltip title={`Delete all data for ${fmtPeriod(selectedPeriods[0])}`}>
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => setDeleteTarget(selectedPeriods[0])}
                  >
                    Delete period
                  </Button>
                </Tooltip>
              )}
            </div>

            {/* ── Metric tiles ─────────────────────────────── */}
            <Row gutter={[16, 16]}>
              {[
                { label: 'Revenue', value: report.pnl.revenue, color: '#6366f1', suffix: '' },
                { label: 'Expenses', value: report.pnl.expenses, color: '#f43f5e', suffix: '' },
                {
                  label: 'Net Profit', value: report.pnl.netProfit,
                  color: report.pnl.netProfit >= 0 ? '#22c55e' : '#f43f5e', suffix: '',
                  icon: report.pnl.netProfit >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
                },
                { label: 'Gross Margin', value: report.pnl.grossMarginPct, color: '#f59e0b', suffix: '%', precision: 1 },
                { label: 'Cash Net', value: report.cashFlow.net, color: '#38bdf8', suffix: '' },
                { label: 'Invoices', value: report.keyMetrics.invoiceCount, color: '#a855f7', suffix: '', precision: 0, isCurrency: false },
              ].map((m) => (
                <Col key={m.label} xs={12} sm={8} md={4}>
                  <Tooltip title={TILE_DOC_TYPES[m.label] ? 'Click to view source documents' : undefined}>
                    <Card
                      size="small"
                      hoverable={!!TILE_DOC_TYPES[m.label]}
                      onClick={() => TILE_DOC_TYPES[m.label] && setActiveTile(m.label)}
                      style={{
                        background: `linear-gradient(135deg, ${cardBg} 0%, ${m.color}18 100%)`,
                        border: `1px solid ${m.color}33`,
                        cursor: TILE_DOC_TYPES[m.label] ? 'pointer' : 'default',
                      }}
                    >
                      <Statistic
                        title={<Text style={{ fontSize: 12, color: '#888' }}>{m.label}</Text>}
                        value={m.value}
                        precision={m.precision ?? 0}
                        suffix={m.suffix}
                        formatter={m.isCurrency === false || m.suffix === '%'
                          ? undefined
                          : (v) => EUR(Number(v))}
                        valueStyle={{ color: m.color, fontSize: 20, fontWeight: 600 }}
                        prefix={m.icon}
                      />
                      {TILE_DOC_TYPES[m.label] && (
                        <FileTextOutlined style={{ position: 'absolute', top: 8, right: 8, color: m.color, opacity: 0.5, fontSize: 11 }} />
                      )}
                    </Card>
                  </Tooltip>
                </Col>
              ))}
            </Row>

            {/* ── Executive Summary ─────────────────────────── */}
            <Card
              style={{ border: `1px solid #6366f133`, background: `linear-gradient(135deg, ${cardBg} 0%, #6366f108 100%)` }}
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <RobotOutlined style={{ color: '#6366f1' }} />
                  <span>Executive Summary</span>
                  <Tag color="purple" style={{ marginLeft: 4 }}>Foundry IQ · Azure AI Search</Tag>
                  {citations.length > 0 && (
                    <Tag color="blue" icon={<LinkOutlined />}>{citations.length} source{citations.length !== 1 ? 's' : ''}</Tag>
                  )}
                </div>
              }
            >
              <Paragraph style={{ lineHeight: 1.9, whiteSpace: 'pre-wrap', margin: 0 }}>
                {summaryBody}
              </Paragraph>
              {citations.length > 0 && (
                <>
                  <Divider style={{ margin: '16px 0 10px' }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>Grounded sources: </Text>
                  {citations.map((c, i) => <Tag key={i} color="geekblue" style={{ fontSize: 11 }}>{c}</Tag>)}
                </>
              )}
            </Card>

            {/* ── Charts row ───────────────────────────────── */}
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={14}>
                <Card title={isMulti ? 'P&L by Period' : 'P&L Overview'} style={{ height: '100%' }}>
                  <ResponsiveContainer width="100%" height={260}>
                    {isMulti ? (
                      <BarChart data={pnlChartData as object[]} margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" vertical={false} />
                        <XAxis dataKey="name" stroke="#555" tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tickFormatter={v => `€${(v / 1000).toFixed(0)}k`} stroke="#555"
                          tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <ReTooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08' }} />
                        <Legend iconType="circle" iconSize={8} formatter={v => <span style={{ color: '#aaa', fontSize: 11 }}>{v}</span>} />
                        <Bar dataKey="Revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Net Profit" fill="#22c55e" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    ) : (
                      <BarChart data={pnlChartData as object[]} margin={{ top: 4, right: 16, left: 8, bottom: 4 }} barCategoryGap="30%">
                        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" vertical={false} />
                        <XAxis dataKey="name" stroke="#555" tick={{ fill: '#888', fontSize: 12 }} axisLine={false} tickLine={false} />
                        <YAxis tickFormatter={v => `€${(v / 1000).toFixed(0)}k`} stroke="#555"
                          tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <ReTooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08' }} />
                        <Bar dataKey="value" name="Amount" radius={[6, 6, 0, 0]} isAnimationActive>
                          {(pnlChartData as { fill: string }[]).map((d, i) => <Cell key={i} fill={d.fill} />)}
                        </Bar>
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                </Card>
              </Col>
              <Col xs={24} lg={10}>
                <Card title="Expense Breakdown" style={{ height: '100%' }}>
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={expenseData} cx="50%" cy="50%"
                        innerRadius={65} outerRadius={100}
                        paddingAngle={4} dataKey="value" isAnimationActive>
                        {expenseData.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <ReTooltip content={<PieCustomTooltip />} />
                      <Legend iconType="circle" iconSize={10}
                        formatter={(v) => <span style={{ color: '#aaa', fontSize: 12 }}>{v}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>

            <Card title="Cash Flow">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={cashChartData} margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                  <defs>
                    <linearGradient id="cfGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" vertical={false} />
                  <XAxis dataKey="name" stroke="#555" tick={{ fill: '#888', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={v => `€${(v / 1000).toFixed(1)}k`} stroke="#555"
                    tick={{ fill: '#888', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <ReTooltip content={<CustomTooltip />} cursor={{ stroke: '#6366f155' }} />
                  <ReferenceLine y={0} stroke="#444" strokeDasharray="4 2" />
                  <Area dataKey="value" name="Cash Flow" stroke="#6366f1" strokeWidth={2}
                    fill="url(#cfGradient)" dot={{ fill: '#6366f1', r: 4 }}
                    activeDot={{ r: 6, fill: '#818cf8' }} isAnimationActive />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            {/* ── Per-period comparison table (multi-select) ── */}
            {isMulti && (
              <Card title="Period Comparison">
                <Table
                  size="small"
                  pagination={false}
                  dataSource={loadedReports.map(r => ({
                    key: r.period,
                    period: fmtPeriod(r.period),
                    revenue: r.pnl.revenue,
                    expenses: r.pnl.expenses,
                    netProfit: r.pnl.netProfit,
                    margin: r.pnl.grossMarginPct,
                    cashNet: r.cashFlow.net,
                    invoices: r.keyMetrics.invoiceCount,
                  }))}
                  columns={[
                    { title: 'Period', dataIndex: 'period', key: 'period' },
                    { title: 'Revenue', dataIndex: 'revenue', key: 'revenue', render: (v: number) => EUR(v), align: 'right' as const },
                    { title: 'Expenses', dataIndex: 'expenses', key: 'expenses', render: (v: number) => EUR(v), align: 'right' as const },
                    { title: 'Net Profit', dataIndex: 'netProfit', key: 'netProfit', render: (v: number) => <span style={{ color: v >= 0 ? '#22c55e' : '#f43f5e' }}>{EUR(v)}</span>, align: 'right' as const },
                    { title: 'Margin', dataIndex: 'margin', key: 'margin', render: (v: number) => `${v.toFixed(1)}%`, align: 'right' as const },
                    { title: 'Cash Net', dataIndex: 'cashNet', key: 'cashNet', render: (v: number) => EUR(v), align: 'right' as const },
                    { title: 'Invoices', dataIndex: 'invoices', key: 'invoices', align: 'right' as const },
                    {
                      title: '', key: 'actions',
                      render: (_: unknown, row: { key: string }) => (
                        <Button danger size="small" icon={<DeleteOutlined />}
                          onClick={() => setDeleteTarget(row.key)} />
                      ),
                    },
                  ]}
                />
              </Card>
            )}

          </Space>
        )}
      </Content>

      {/* ── Upload drawer ────────────────────────────────────── */}
      <Drawer
        title="Upload Documents"
        placement="right"
        width={520}
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        destroyOnClose
        styles={{ body: { padding: 0 } }}
      >
        <UploadPage
          onComplete={(period) => {
            setUploadOpen(false)
            queryClient.invalidateQueries({ queryKey: ['periods'] })
            setSelectedPeriods([period])
          }}
        />
      </Drawer>

      {/* ── Tile drill-down modal ─────────────────────────────── */}
      <Modal
        title={
          <Space>
            <FileTextOutlined style={{ color: '#6366f1' }} />
            {activeTile} Breakdown
          </Space>
        }
        open={!!activeTile}
        onCancel={() => setActiveTile(null)}
        footer={null}
        width={700}
      >
        {activeTile && (
          docsLoading
            ? <div style={{ textAlign: 'center', padding: 32 }}><Spin tip="Loading documents…" /></div>
            : <Table
                size="small"
                pagination={{ pageSize: 20, size: 'small' }}
                columns={DOC_COLUMNS}
                dataSource={allDocs.filter(d => TILE_DOC_TYPES[activeTile]?.includes(d.doc_type))}
                rowKey={(d) => `${d.period}-${d.source_file}`}
                locale={{ emptyText: 'No documents found for this category' }}
              />
        )}
      </Modal>

      {/* ── Delete confirmation modal ─────────────────────────── */}
      <Modal
        title={<Space><DeleteOutlined style={{ color: '#f43f5e' }} />Delete period data</Space>}
        open={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onOk={() => deleteTarget && deleteMutation.mutate(deleteTarget)}
        okText="Delete"
        okButtonProps={{ danger: true, loading: deleteMutation.isPending }}
        cancelText="Cancel"
      >
        <Text>
          This will permanently delete all extracted documents and the cached report for{' '}
          <strong>{deleteTarget ? fmtPeriod(deleteTarget) : ''}</strong>.
          This action cannot be undone.
        </Text>
      </Modal>
    </Layout>
  )
}
