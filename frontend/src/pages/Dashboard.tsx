import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Layout, Typography, Row, Col, Card, Button, Spin, Alert, Space, theme, Result,
} from 'antd'
import { ArrowLeftOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import PnLChart from '../components/PnLChart'
import CashFlowChart from '../components/CashFlowChart'
import ExpenseBreakdown from '../components/ExpenseBreakdown'
import MetricsCards from '../components/MetricsCards'
import ExecutiveSummary from '../components/ExecutiveSummary'

const { Content } = Layout
const { Title, Text } = Typography
const { useToken } = theme

export default function DashboardPage() {
  const { period } = useParams<{ period: string }>()
  const navigate = useNavigate()
  const { token } = useToken()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['report', period],
    queryFn: () => api.getReport(period!),
    enabled: !!period,
    retry: (failureCount, err) => {
      // never retry on 4xx — only on network errors or 5xx
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status && status >= 400 && status < 500) return false
      return failureCount < 2
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyze(period!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['report', period] }),
  })

  if (isLoading) {
    return (
      <Layout style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" tip="Loading financial report..." />
      </Layout>
    )
  }

  // 404 — report not yet generated for this period
  const status = (error as { response?: { status?: number } })?.response?.status
  if (!data && status === 404) {
    return (
      <Layout style={{ minHeight: '100vh', padding: 48 }}>
        <Result
          status="info"
          title={`No report for ${period} yet`}
          subTitle="Run the 7-agent analysis pipeline to generate a financial report for this period."
          extra={[
            <Button
              key="analyze"
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              loading={analyzeMutation.isPending}
              onClick={() => analyzeMutation.mutate()}
            >
              {analyzeMutation.isPending ? 'Running analysis (30–90s)…' : 'Run Analysis'}
            </Button>,
            <Button key="back" onClick={() => navigate('/upload')}>
              <ArrowLeftOutlined /> New upload
            </Button>,
          ]}
        />
        {analyzeMutation.isError && (
          <Alert
            type="error"
            message="Analysis failed"
            description={String(analyzeMutation.error)}
            style={{ marginTop: 24 }}
          />
        )}
      </Layout>
    )
  }

  if (error || !data) {
    return (
      <Layout style={{ minHeight: '100vh', padding: 48 }}>
        <Alert
          type="error"
          message="Failed to load report"
          description={error instanceof Error ? error.message : 'Unknown error'}
          action={<Button onClick={() => navigate('/upload')}>Go back</Button>}
        />
      </Layout>
    )
  }

  const { report } = data

  return (
    <Layout style={{ minHeight: '100vh', background: token.colorBgLayout }}>
      <Content style={{ maxWidth: 1400, margin: '0 auto', padding: '32px 24px' }}>
        <Space direction="vertical" size={24} style={{ width: '100%' }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/upload')}>
                New upload
              </Button>
            </Col>
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                Financial Report — {period}
              </Title>
            </Col>
            <Col>
              <Text type="secondary">
                Generated {new Date(report.generatedAt).toLocaleString()}
              </Text>
            </Col>
          </Row>

          <MetricsCards metrics={report.keyMetrics} pnl={report.pnl} />

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={16}>
              <Card title="Revenue vs Expenses vs Net Profit">
                <PnLChart data={report.pnl} />
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card title="Expense Breakdown">
                <ExpenseBreakdown data={report.expenseBreakdown} />
              </Card>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <Card title="Cash Flow">
                <CashFlowChart data={report.cashFlow} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Executive Summary">
                <ExecutiveSummary summary={report.executiveSummary} period={period!} />
              </Card>
            </Col>
          </Row>
        </Space>
      </Content>
    </Layout>
  )
}
