import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { cn, formatRelativeTime, getSeverityColor, getRecommendationColor, formatDateTime } from '@/lib/utils'
import { evidenceApi, casesApi } from '@/lib/api'
import { EvidenceAtom, FusionResult } from '@/lib/api'
import {
  ArrowLeft,
  ListChecks,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Info,
  Shield,
  Zap,
  HelpCircle,
  Search,
  Filter,
  Gauge,
  Network,
  FileText,

} from 'lucide-react'

const sourceIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  OCR: FileText,
  MRZ: FileText,
  BARCODE: FileText,
  DOCUMENT_VALIDATION: Shield,
  TAMPER_ANALYSIS: Shield,
  FACE_VERIFICATION: Zap,
  LIVENESS: Zap,
  IDENTITY_GRAPH: Network,
  WATCHLIST: AlertTriangle,
  VISA_RULES: Gauge,
  FRESHNESS: RefreshCw,
}

export function EvidenceView() {
  const { caseId } = useParams<{ caseId: string }>()
  const [atoms, setAtoms] = useState<EvidenceAtom[]>([])
  const [fusion, setFusion] = useState<FusionResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [sourceFilter, setSourceFilter] = useState<string>('all')

  const fetchEvidence = useCallback(async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const [atomsRes, fusionRes] = await Promise.all([
        evidenceApi.list(caseId).catch(() => ({ data: [] })),
        evidenceApi.getFusion(caseId).catch(() => ({ data: null })),
      ])
      setAtoms(atomsRes.data)
      setFusion(fusionRes.data)
    } catch (err) {
      setError('Failed to load evidence')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    fetchEvidence()
  }, [fetchEvidence])

  const handleGenerate = async () => {
    if (!caseId) return
    setGenerating(true)
    setError(null)
    try {
      await evidenceApi.generate(caseId)
      await fetchEvidence()
    } catch (err) {
      setError('Failed to generate evidence atoms')
    } finally {
      setGenerating(false)
    }
  }

  const filteredAtoms = atoms.filter((a) => {
    const matchesSearch =
      a.evidence_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.source.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesSeverity = severityFilter === 'all' || a.severity === severityFilter
    const matchesSource = sourceFilter === 'all' || a.source === sourceFilter
    return matchesSearch && matchesSeverity && matchesSource
  })

  const severities = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
  const sources = [...new Set(atoms.map((a) => a.source))]

  const sortedAtoms = [...filteredAtoms].sort((a, b) => {
    const order = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 }
    return order[a.severity as keyof typeof order] - order[b.severity as keyof typeof order]
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading evidence...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to={`/case/${caseId}`} className="btn-ghost p-2">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <ListChecks className="h-6 w-6 text-primary-600" />
              Evidence & Fusion
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Explainable evidence atoms and risk fusion
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchEvidence} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button onClick={handleGenerate} className="btn-primary" disabled={generating}>
            {generating ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 mr-2" />
                Generate Evidence
              </>
            )}
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

      {/* Fusion Summary */}
      {fusion && (
        <div className="card border-l-4 border-l-primary-600">
          <div className="card-header">
            <div className="flex items-center justify-between">
              <h2 className="card-title">Fusion Recommendation</h2>
              <span className={cn('badge px-3 py-1 text-lg', getRecommendationColor(fusion.recommendation))}>
                {fusion.recommendation.replace('_', ' ')}
              </span>
            </div>
          </div>
          <div className="card-content space-y-4">
            {/* Score breakdown */}
            <div className="grid grid-cols-3 gap-4">
              <ScoreBar label="Positive" value={fusion.positive_score} color="green" />
              <ScoreBar label="Negative" value={fusion.negative_score} color="red" />
              <ScoreBar label="Net" value={fusion.net_score} color="blue" />
            </div>

            {/* Confidence */}
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-1">
                  <span>Confidence</span>
                  <span>{(fusion.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={cn('h-2 rounded-full', confidenceColor(fusion.confidence))}
                    style={{ width: `${fusion.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="font-medium text-gray-900 dark:text-white mb-1">Reasoning</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">{fusion.reasoning}</p>
            </div>

            {/* Data freshness */}
            {(fusion.stale_evidence_count > 0 || fusion.unavailable_evidence_count > 0 || fusion.adverse_evidence_count > 0) && (
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="font-medium text-yellow-800 dark:text-yellow-200 mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Data Freshness Warnings
                </p>
                <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                  {fusion.stale_evidence_count > 0 && (
                    <li>• {fusion.stale_evidence_count} evidence items from stale data</li>
                  )}
                  {fusion.unavailable_evidence_count > 0 && (
                    <li>• {fusion.unavailable_evidence_count} evidence items unavailable</li>
                  )}
                  {fusion.adverse_evidence_count > 0 && (
                    <li>• {fusion.adverse_evidence_count} confirmed adverse records</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-content flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-400" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="input w-auto"
              >
                <option value="all">All Severities</option>
                {severities.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="input w-auto"
              >
                <option value="all">All Sources</option>
                {sources.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Atoms */}
      {sortedAtoms.length === 0 ? (
        <div className="card border-dashed">
          <div className="card-content text-center py-8">
            <HelpCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Evidence Atoms</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Generate evidence from OCR, MRZ, barcode, validation, tamper, face, and graph analysis
            </p>
            <button onClick={handleGenerate} className="btn-primary">
              <Zap className="h-4 w-4 mr-2" />
              Generate Evidence
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sortedAtoms.map((atom) => (
            <EvidenceCard key={atom.id} atom={atom} />
          ))}
        </div>
      )}

      {/* Limitations */}
      {fusion && (
        <div className="card border-gray-200 dark:border-gray-700">
          <div className="card-header">
            <h2 className="card-title">Prototype Limitations</h2>
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
      )}
    </div>
  )
}

function EvidenceCard({ atom }: { atom: EvidenceAtom }) {
  const Icon = sourceIcons[atom.source] || FileText
  const isConcern = ['CRITICAL', 'HIGH'].includes(atom.severity)

  return (
    <div
      className={cn(
        'card',
        isConcern && 'border-red-200 dark:border-red-800',
        atom.freshness === 'CONFIRMED_ADVERSE' && 'border-red-400 dark:border-red-600'
      )}
    >
      <div className="card-content">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <div className={cn('p-2 rounded-lg flex-shrink-0', isConcern ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30')}>
              <Icon className={cn('h-5 w-5', isConcern ? 'text-red-600' : 'text-green-600')} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn('badge', getSeverityColor(atom.severity))}>
                  {atom.severity}
                </span>
                <span className="badge badge-gray">{atom.source}</span>
                {atom.freshness === 'VERIFIED_STALE' && (
                  <span className="badge badge-warning">STALE</span>
                )}
                {atom.freshness === 'UNAVAILABLE' && (
                  <span className="badge badge-destructive">UNAVAILABLE</span>
                )}
                {atom.freshness === 'CONFIRMED_ADVERSE' && (
                  <span className="badge badge-destructive">ADVERSE</span>
                )}
              </div>
              <p className="font-mono text-sm font-medium mt-2 text-gray-900 dark:text-white">
                {atom.evidence_type}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {atom.description}
              </p>
              {atom.explanation && (
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-2 italic">
                  {atom.explanation}
                </p>
              )}
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-sm font-bold text-primary-600">
              {(atom.confidence * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-gray-500">confidence</p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500">
          <span>v{atom.rule_or_model_version || '1.0'}</span>
          {atom.last_synced_at && (
            <span>Synced {formatRelativeTime(atom.last_synced_at)}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    green: 'bg-green-500',
    red: 'bg-red-500',
    blue: 'bg-blue-500',
  }

  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value.toFixed(2)}</p>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1 mt-2">
        <div
          className={cn('h-1 rounded-full', colors[color])}
          style={{ width: `${Math.min(Math.abs(value) * 100, 100)}%` }}
        />
      </div>
    </div>
  )
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-green-500'
  if (confidence >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}