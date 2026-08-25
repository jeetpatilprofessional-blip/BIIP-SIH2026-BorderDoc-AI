import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { cn, formatDateTime, formatRelativeTime, getRecommendationColor, getSeverityColor } from '@/lib/utils'
import { casesApi, documentsApi, evidenceApi, faceApi } from '@/lib/api'
import { Case, Document, FaceResult, FusionResult } from '@/lib/api'
import {
  ArrowLeft,
  FileText,
  GitBranch,
  ListChecks,
  ClipboardList,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Shield,
  Clock,
  RefreshCw,
  Download,
  Eye,
  Zap,
} from 'lucide-react'

export function CaseDetails() {
  const { caseId } = useParams<{ caseId: string }>()
  const [caseData, setCaseData] = useState<Case | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [fusion, setFusion] = useState<FusionResult | null>(null)
  const [faceResults, setFaceResults] = useState<FaceResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'face' | 'fusion'>('overview')

  const fetchData = async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const [caseRes, docsRes, fusionRes, facesRes] = await Promise.all([
        casesApi.get(caseId),
        documentsApi.list(caseId),
        evidenceApi.getFusion(caseId).catch(() => ({ data: null })),
        faceApi.list(caseId).catch(() => ({ data: [] })),
      ])
      setCaseData(caseRes.data)
      setDocuments(docsRes.data)
      setFusion(fusionRes.data)
      setFaceResults(facesRes.data)
    } catch (err) {
      setError('Failed to load case details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [caseId])

  if (!caseData && loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading case...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
          <button onClick={fetchData} className="btn-primary mt-4">
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!caseData) return null

  const recommendation = fusion?.recommendation
  const recommendationColor = recommendation ? getRecommendationColor(recommendation) : 'badge-gray'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/screening" className="btn-ghost p-2">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Case {caseData.case_number}
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              {caseData.location} • {caseData.checkpoint_type} • {formatRelativeTime(caseData.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn('badge px-3 py-1 text-sm', recommendationColor)}>
            {recommendation?.replace('_', ' ') || 'PENDING'}
          </span>
          <span className={cn('badge px-3 py-1 text-sm', statusColors[caseData.status] || 'badge-gray')}>
            {caseData.status.replace('_', ' ')}
          </span>
          <button onClick={fetchData} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-red-700 dark:text-red-300 flex-1">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4" aria-label="Case tabs">
          <TabButton
            active={activeTab === 'overview'}
            onClick={() => setActiveTab('overview')}
            icon={Shield}
            label="Overview"
            count={1}
          />
          <TabButton
            active={activeTab === 'documents'}
            onClick={() => setActiveTab('documents')}
            icon={FileText}
            label="Documents"
            count={documents.length}
          />
          <TabButton
            active={activeTab === 'face'}
            onClick={() => setActiveTab('face')}
            icon={Zap}
            label="Face Verification"
            count={faceResults.length}
          />
          <TabButton
            active={activeTab === 'fusion'}
            onClick={() => setActiveTab('fusion')}
            icon={ListChecks}
            label="Evidence Fusion"
            count={fusion ? 1 : 0}
          />
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab caseData={caseData} fusion={fusion} />}
      {activeTab === 'documents' && <DocumentsTab documents={documents} caseId={caseId!} />}
      {activeTab === 'face' && <FaceTab faceResults={faceResults} caseId={caseId!} />}
      {activeTab === 'fusion' && <FusionTab fusion={fusion} />}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
  count,
}: {
  active: boolean
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  label: string
  count: number
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
        active
          ? 'border-primary-600 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
      {count > 0 && (
        <span className={cn('px-2 py-0.5 text-xs rounded-full', active ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600')}>
          {count}
        </span>
      )}
    </button>
  )
}

const statusColors: Record<string, string> = {
  OPEN: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  PENDING_REVIEW: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  CLOSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  ESCALATED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

function OverviewTab({ caseData, fusion }: { caseData: Case; fusion: FusionResult | null }) {
  return (
    <div className="space-y-6 mt-6">
      {/* Case Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <InfoCard title="Case Number" value={caseData.case_number} icon={FileText} />
        <InfoCard title="Status" value={caseData.status.replace('_', ' ')} icon={Shield} badgeClass={statusColors[caseData.status] || 'badge-gray'} />
        <InfoCard title="Priority" value={`P${caseData.priority}`} icon={AlertTriangle} />
        <InfoCard title="Officer" value={caseData.officer_id} icon={ClipboardList} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <InfoCard title="Location" value={caseData.location} icon={HelpCircle} />
        <InfoCard title="Checkpoint" value={caseData.checkpoint_type} icon={Clock} />
        <InfoCard title="Created" value={formatDateTime(caseData.created_at)} icon={Clock} />
        <InfoCard title="Person ID" value={caseData.person_id || 'Not linked'} icon={Eye} />
      </div>

      {/* Fusion Summary */}
      {fusion && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Evidence Fusion Summary</h2>
            <p className="card-description">Automated analysis recommendation</p>
          </div>
          <div className="card-content space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className={cn('badge px-3 py-1 text-lg', getRecommendationColor(fusion.recommendation))}>
                  {fusion.recommendation.replace('_', ' ')}
                </span>
                <span className="ml-3 text-sm text-gray-500">
                  Confidence: {(fusion.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <p className="text-gray-700 dark:text-gray-300">{fusion.reasoning}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-gray-500">Evidence Atoms</p>
                <p className="font-bold">{fusion.evidence_atoms_considered}</p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-gray-500">Stale</p>
                <p className="font-bold text-orange-600">{fusion.stale_evidence_count}</p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-gray-500">Unavailable</p>
                <p className="font-bold text-red-600">{fusion.unavailable_evidence_count}</p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-gray-500">Adverse</p>
                <p className="font-bold text-red-600">{fusion.adverse_evidence_count}</p>
              </div>
            </div>
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <p className="font-medium text-yellow-800 dark:text-yellow-200">Recommended Action:</p>
              <p className="text-yellow-700 dark:text-yellow-300 mt-1">{fusion.recommended_action}</p>
            </div>
          </div>
        </div>
      )}

      {!fusion && (
        <div className="card border-dashed">
          <div className="card-content text-center py-8">
            <HelpCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Fusion Analysis</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Generate evidence atoms and run fusion to get a recommendation
            </p>
            <Link to={`/case/${caseData.id}/evidence`} className="btn-primary">
              Go to Evidence
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function DocumentsTab({ documents, caseId }: { documents: Document[]; caseId: string }) {
  const docTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
    PASSPORT: FileText,
    VISA: FileText,
    NATIONAL_ID: FileText,
    DRIVING_LICENSE: FileText,
  }

  return (
    <div className="mt-6">
      <div className="card">
        <div className="table-container">
          <table className="table">
            <thead className="table-header">
              <tr>
                <th className="table-head">Type</th>
                <th className="table-head">Number</th>
                <th className="table-head">Country</th>
                <th className="table-head">MRZ</th>
                <th className="table-head">Barcode</th>
                <th className="table-head">Status</th>
                <th className="table-head">Actions</th>
              </tr>
            </thead>
            <tbody className="table-body">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-cell text-center py-8">
                    <p className="text-gray-500">No documents uploaded</p>
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="table-row">
                    <td className="table-cell">
                      <span className="badge badge-info">{doc.document_type}</span>
                    </td>
                    <td className="table-cell font-mono">{doc.document_number || '-'}</td>
                    <td className="table-cell">{doc.country_code || '-'}</td>
                    <td className="table-cell">
                      {doc.mrz_raw ? (
                        <span className={cn('badge', doc.mrz_valid ? 'badge-success' : 'badge-destructive')}>
                          {doc.mrz_valid ? 'Valid' : 'Invalid'}
                        </span>
                      ) : (
                        <span className="badge badge-gray">None</span>
                      )}
                    </td>
                    <td className="table-cell">
                      {doc.barcode_raw ? (
                        <span className="badge badge-success">Present</span>
                      ) : (
                        <span className="badge badge-gray">None</span>
                      )}
                    </td>
                    <td className="table-cell">
                      <span className={cn('badge', processingStatusColor(doc.processing_status))}>
                        {doc.processing_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="table-cell">
                      <Link
                        to={`/case/${caseId}/documents/${doc.id}`}
                        className="btn-ghost btn-sm"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function FaceTab({ faceResults, caseId }: { faceResults: FaceResult[]; caseId: string }) {
  return (
    <div className="mt-6 space-y-4">
      {faceResults.length === 0 ? (
        <div className="card border-dashed">
          <div className="card-content text-center py-8">
            <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Face Captures</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Capture a live face to perform verification and liveness checks
            </p>
            <button className="btn-primary">Capture Face</button>
          </div>
        </div>
      ) : (
        faceResults.map((face) => (
          <div key={face.id} className="card">
            <div className="card-content">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
                    <Zap className="h-8 w-8 text-gray-400" />
                  </div>
                  <div>
                    <p className="font-medium">Live Capture</p>
                    <p className="text-sm text-gray-500">{formatRelativeTime(face.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {face.quality_score !== undefined && (
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Quality</p>
                      <p className="font-bold text-lg">
                        {(face.quality_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  )}
                  {face.match_score !== undefined && (
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Match Score</p>
                      <p className={cn('font-bold text-lg', face.match_result === 'MATCH' ? 'text-green-600' : face.match_result === 'MISMATCH' ? 'text-red-600' : 'text-yellow-600')}>
                        {(face.match_score * 100).toFixed(0)}%
                      </p>
                      <span className={cn('badge ml-2', face.match_result === 'MATCH' ? 'badge-success' : face.match_result === 'MISMATCH' ? 'badge-destructive' : 'badge-warning')}>
                        {face.match_result}
                      </span>
                    </div>
                  )}
                  {face.liveness_result && (
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Liveness</p>
                      <span className={cn('badge', livenessBadgeColor(face.liveness_result))}>
                        {face.liveness_result.replace('_', ' ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function FusionTab({ fusion }: { fusion: FusionResult | null }) {
  if (!fusion) {
    return (
      <div className="mt-6 card border-dashed">
        <div className="card-content text-center py-8">
          <HelpCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Fusion Analysis</h3>
          <p className="text-gray-500 dark:text-gray-400">
            Run evidence generation to see fusion results
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-6 space-y-6">
      {/* Primary Reasons */}
      {fusion.primary_reasons.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Primary Concerns</h2>
          </div>
          <div className="card-content">
            <ul className="space-y-2">
              {fusion.primary_reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-red-700 dark:text-red-300">{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Supporting Evidence */}
      {fusion.supporting_evidence.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Supporting Evidence</h2>
          </div>
          <div className="card-content">
            <div className="space-y-2">
              {fusion.supporting_evidence.map((e) => (
                <EvidenceRow key={e.evidence_id} evidence={e} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Contradicting Evidence */}
      {fusion.contradicting_evidence.length > 0 && (
        <div className="card border-red-200 dark:border-red-800">
          <div className="card-header">
            <h2 className="card-title text-red-700 dark:text-red-300">Contradicting Evidence</h2>
          </div>
          <div className="card-content">
            <div className="space-y-2">
              {fusion.contradicting_evidence.map((e) => (
                <EvidenceRow key={e.evidence_id} evidence={e} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Freshness Warnings */}
      {fusion.data_freshness_warnings.length > 0 && (
        <div className="card border-yellow-200 dark:border-yellow-800">
          <div className="card-header">
            <h2 className="card-title text-yellow-700 dark:text-yellow-300">Data Freshness Warnings</h2>
          </div>
          <div className="card-content">
            <ul className="space-y-1">
              {fusion.data_freshness_warnings.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-yellow-700 dark:text-yellow-300">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Limitations */}
      <div className="card border-gray-200 dark:border-gray-700">
        <div className="card-header">
          <h2 className="card-title">Limitations</h2>
        </div>
        <div className="card-content">
          <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {fusion.limitations.map((l, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-primary-600">•</span>
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

function EvidenceRow({ evidence }: { evidence: any }) {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <div className="flex items-center gap-3">
        <span className={cn('badge', getSeverityColor(evidence.severity))}>
          {evidence.severity}
        </span>
        <div>
          <p className="font-medium text-sm">{evidence.evidence_type}</p>
          <p className="text-xs text-gray-500">{evidence.description}</p>
        </div>
      </div>
      <div className="text-right text-sm">
        <p className="font-bold text-primary-600">
          {evidence.contribution > 0 ? '+' : ''}{evidence.contribution.toFixed(3)}
        </p>
        <p className="text-gray-500">Weight: {evidence.weight.toFixed(3)}</p>
      </div>
    </div>
  )
}

function InfoCard({
  title,
  value,
  icon: Icon,
  badgeClass,
}: {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  badgeClass?: string
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="font-medium text-gray-900 dark:text-white mt-1">{value}</p>
        </div>
        <Icon className="h-6 w-6 text-gray-400" />
      </div>
    </div>
  )
}

function processingStatusColor(status: string): string {
  switch (status) {
    case 'UPLOADED':
      return 'badge-gray'
    case 'PROCESSING':
      return 'badge-warning'
    case 'COMPLETED':
      return 'badge-success'
    case 'FAILED':
      return 'badge-destructive'
    default:
      return 'badge-gray'
  }
}

function livenessBadgeColor(result: string): string {
  switch (result) {
    case 'LIVE':
      return 'badge-success'
    case 'SPOOF_SUSPECTED':
      return 'badge-destructive'
    case 'INCONCLUSIVE':
      return 'badge-warning'
    default:
      return 'badge-gray'
  }
}