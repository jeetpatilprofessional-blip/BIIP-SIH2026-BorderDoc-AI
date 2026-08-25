import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { cn, formatRelativeTime } from '@/lib/utils'
import { demoApi, casesApi, documentsApi, faceApi, evidenceApi } from '@/lib/api'
import { DemoScenario, Case, Document } from '@/lib/api'
import {
  FlaskConical,
  RefreshCw,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  Upload,
  Zap,
  Eye,
  Download,
  Settings,
  Trash2,
  Plus,
} from 'lucide-react'

export function DemoLab() {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([])
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runningScenario, setRunningScenario] = useState<string | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [scenariosRes, casesRes] = await Promise.all([
        demoApi.getScenarios().catch(() => ({ data: [] })),
        casesApi.list({ limit: 100 }).catch(() => ({ data: { cases: [] } })),
      ])
      setScenarios(scenariosRes.data)
      setCases(casesRes.data.cases)
    } catch (err) {
      setError('Failed to load demo data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRunScenario = async (scenarioId: string) => {
    setRunningScenario(scenarioId)
    setError(null)
    try {
      const response = await demoApi.runScenario(scenarioId)
      // Navigate to the new case
      window.location.href = `/case/${response.data.case_id}`
    } catch (err) {
      setError('Failed to run scenario')
    } finally {
      setRunningScenario(null)
    }
  }

  const handleLoadTestData = async () => {
    setError(null)
    try {
      await demoApi.loadTestData()
      await fetchData()
    } catch (err) {
      setError('Failed to load test data')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading demo lab...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-primary-600" />
            Demo Lab
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Pre-configured test scenarios and synthetic data generation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchData} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button onClick={handleLoadTestData} className="btn-secondary">
            <Download className="h-4 w-4 mr-2" />
            Load Test Data
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-red-700 dark:text-red-300 flex-1">{error}</p>
        </div>
      )}

      {/* Scenarios */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            Test Scenarios
          </h2>
        </div>
        <div className="card-content">
          {scenarios.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FlaskConical className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No scenarios available</p>
              <button onClick={handleLoadTestData} className="btn-primary mt-4">
                Load Test Data
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {scenarios.map((scenario) => (
                <ScenarioCard
                  key={scenario.id}
                  scenario={scenario}
                  running={runningScenario === scenario.id}
                  onRun={() => handleRunScenario(scenario.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Cases */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="card-title flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Recent Cases
          </h2>
          <Link to="/screening" className="text-sm text-primary-600 hover:underline">
            View All
          </Link>
        </div>
        <div className="card-content">
          {cases.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No cases yet</p>
              <p className="text-sm">Run a scenario to create a case</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    <th className="table-head">Case Number</th>
                    <th className="table-head">Status</th>
                    <th className="table-head">Location</th>
                    <th className="table-head">Documents</th>
                    <th className="table-head">Created</th>
                    <th className="table-head">Actions</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {cases.slice(0, 10).map((c) => (
                    <tr key={c.id} className="table-row">
                      <td className="table-cell font-mono font-medium">{c.case_number}</td>
                      <td className="table-cell">
                        <span className={cn('badge', caseStatusColor(c.status))}>
                          {c.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="table-cell">{c.location}</td>
                      <td className="table-cell">
                        <span className="badge badge-gray">Click to view</span>
                      </td>
                      <td className="table-cell text-gray-500">
                        {formatRelativeTime(c.created_at)}
                      </td>
                      <td className="table-cell">
                        <Link to={`/case/${c.id}`} className="btn-ghost btn-sm">
                          <Eye className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Manual Testing */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Manual Testing
          </h2>
        </div>
        <div className="card-content space-y-6">
          <div>
            <h3 className="font-medium mb-4">Upload Test Document</h3>
            <DocumentUpload />
          </div>
          <div>
            <h3 className="font-medium mb-4">Quick Actions</h3>
            <div className="flex flex-wrap gap-3">
              <Link to="/screening" className="btn-outline">
                <Plus className="h-4 w-4 mr-2" />
                Create Case
              </Link>
              <button className="btn-outline">
                <Zap className="h-4 w-4 mr-2" />
                Run Full Pipeline
              </button>
              <button className="btn-outline">
                <Download className="h-4 w-4 mr-2" />
                Export Test Report
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ScenarioCard({
  scenario,
  running,
  onRun,
}: {
  scenario: DemoScenario
  running: boolean
  onRun: () => void
}) {
  const recommendationColor: Record<string, string> = {
    LOW_CONCERN: 'badge-success',
    SECONDARY_INSPECTION: 'badge-warning',
    HIGH_CONCERN: 'badge-destructive',
    INSUFFICIENT_EVIDENCE: 'badge-gray',
  }

  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-gray-900 dark:text-white">{scenario.name}</h3>
        <span className={cn('badge', recommendationColor[scenario.expected_recommendation] || 'badge-gray')}>
          {scenario.expected_recommendation.replace('_', ' ')}
        </span>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 flex-1">
        {scenario.description}
      </p>

      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <span className="badge badge-gray">{scenario.documents.length} docs</span>
        <span className="badge badge-gray">{scenario.face_scenario}</span>
      </div>
      <button
        onClick={onRun}
        disabled={running}
        className="btn-primary w-full mt-auto"
      >
        {running ? (
          <>
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Run Scenario
          </>
        )}
      </button>
    </div>
  )
}

function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState('PASSPORT')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    try {
      // This would need a case ID - in demo, we'd create one first
      // For now just simulate
      await new Promise((resolve) => setTimeout(resolve, 2000))
      setProgress(100)
      alert('Document uploaded! (Demo - would process in real case)')
    } catch (err) {
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-end">
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="input"
        >
          <option value="PASSPORT">Passport</option>
          <option value="VISA">Visa</option>
          <option value="NATIONAL_ID">National ID</option>
          <option value="DRIVING_LICENSE">Driving License</option>
        </select>
      </div>
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1">File</label>
        <input
          type="file"
          accept="image/*,application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="input"
        />
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="btn-primary"
        >
          {uploading ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Uploading... {progress}%
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload
            </>
          )}
        </button>
        {file && (
          <span className="text-sm text-gray-500">{file.name}</span>
        )}
      </div>
    </div>
  )
}

function caseStatusColor(status: string): string {
  switch (status) {
    case 'OPEN':
      return 'badge-info'
    case 'IN_PROGRESS':
      return 'badge-warning'
    case 'PENDING_REVIEW':
      return 'badge-warning'
    case 'CLOSED':
      return 'badge-success'
    case 'ESCALATED':
      return 'badge-destructive'
    default:
      return 'badge-gray'
  }
}