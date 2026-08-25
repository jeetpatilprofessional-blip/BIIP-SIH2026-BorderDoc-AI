import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { cn, formatDateTime, formatRelativeTime } from '@/lib/utils'
import { auditApi } from '@/lib/api'
import { AuditLog } from '@/lib/api'
import {
  ArrowLeft,
  ClipboardList,
  RefreshCw,
  AlertTriangle,
  Shield,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
} from 'lucide-react'

const actionIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  CASE_CREATED: ClipboardList,
  CASE_UPDATED: ClipboardList,
  DOCUMENT_UPLOADED: Shield,
  DOCUMENT_PROCESSED: Shield,
  OCR_COMPLETED: Eye,
  MRZ_PARSED: Eye,
  BARCODE_READ: Eye,
  FACE_CAPTURED: Shield,
  FACE_VERIFIED: Shield,
  LIVENESS_CHECKED: Shield,
  TAMPER_CHECKED: AlertTriangle,
  VALIDATION_COMPLETED: Shield,
  EVIDENCE_GENERATED: ClipboardList,
  FUSION_COMPLETED: ClipboardList,
  RECOMMENDATION_VIEWED: ClipboardList,
  OFFICER_DECISION: Shield,
  CASE_CLOSED: ClipboardList,
  STATUS_CHECK_REQUESTED: RefreshCw,
  STATUS_CHECK_COMPLETED: RefreshCw,
  SYNC_TRIGGERED: RefreshCw,
  SYNC_COMPLETED: RefreshCw,
  RULE_SET_UPDATED: Shield,
  MODEL_UPDATED: Shield,
  SYSTEM_ERROR: AlertTriangle,
  ACCESS_DENIED: AlertTriangle,
  EXPORT_REQUESTED: Download,
}

const actionColors: Record<string, string> = {
  CASE_CREATED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  CASE_UPDATED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  DOCUMENT_UPLOADED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  DOCUMENT_PROCESSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  OCR_COMPLETED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  MRZ_PARSED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  BARCODE_READ: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  FACE_CAPTURED: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  FACE_VERIFIED: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  LIVENESS_CHECKED: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  TAMPER_CHECKED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  VALIDATION_COMPLETED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  EVIDENCE_GENERATED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  FUSION_COMPLETED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  RECOMMENDATION_VIEWED: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  OFFICER_DECISION: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  CASE_CLOSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  STATUS_CHECK_REQUESTED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  STATUS_CHECK_COMPLETED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  SYNC_TRIGGERED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  SYNC_COMPLETED: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  RULE_SET_UPDATED: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  MODEL_UPDATED: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  SYSTEM_ERROR: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  ACCESS_DENIED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  EXPORT_REQUESTED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
}

const resultColors: Record<string, string> = {
  SUCCESS: 'badge-success',
  FAILURE: 'badge-destructive',
  WARNING: 'badge-warning',
}

export function AuditTrail() {
  const { caseId } = useParams<{ caseId: string }>()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [actionFilter, setActionFilter] = useState<string>('all')
  const [resultFilter, setResultFilter] = useState<string>('all')
  const [chainVerified, setChainVerified] = useState<{ intact: boolean; brokenLinks: number } | null>(null)

  const pageSize = 50

  const fetchLogs = useCallback(async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const response = await auditApi.getCaseTrail(caseId, pageSize)
      setLogs(response.data)
      setTotal(response.data.length)
    } catch (err) {
      setError('Failed to load audit trail')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  const verifyChain = useCallback(async () => {
    if (!caseId) return
    try {
      const response = await auditApi.verifyChain(caseId)
      setChainVerified({
        intact: response.data.intact,
        brokenLinks: response.data.broken_links,
      })
    } catch (err) {
      setError('Failed to verify chain')
    }
  }, [caseId])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.actor_id.toLowerCase().includes(search.toLowerCase()) ||
      (log.entity_type?.toLowerCase().includes(search.toLowerCase()) ?? false) ||
      (log.entity_id?.toLowerCase().includes(search.toLowerCase()) ?? false)
    const matchesAction = actionFilter === 'all' || log.action === actionFilter
    const matchesResult = resultFilter === 'all' || log.result === resultFilter
    return matchesSearch && matchesAction && matchesResult
  })

  const actions = [...new Set(logs.map((l) => l.action))].sort()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading audit trail...</p>
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
              <ClipboardList className="h-6 w-6 text-primary-600" />
              Audit Trail
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Immutable log of all system actions and officer decisions
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={verifyChain} className="btn-outline">
            <Shield className="h-4 w-4 mr-2" />
            Verify Chain
          </button>
          <button onClick={fetchLogs} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button className="btn-outline">
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Chain Verification Result */}
      {chainVerified && (
        <div className={cn('card', chainVerified.intact ? 'border-green-200' : 'border-red-200')}>
          <div className="card-content flex items-center gap-4">
            {chainVerified.intact ? (
              <CheckCircle className="h-6 w-6 text-green-600" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-red-600" />
            )}
            <div>
              <p className="font-medium">
                {chainVerified.intact ? 'Chain Integrity Verified' : 'Chain Integrity Broken'}
              </p>
              <p className="text-sm text-gray-500">
                {chainVerified.intact
                  ? 'All audit entries form an unbroken cryptographic chain'
                  : `${chainVerified.brokenLinks} broken link(s) detected`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-red-700 dark:text-red-300 flex-1">{error}</p>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-content flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search audit log..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-3">
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Actions</option>
              {actions.map((a) => (
                <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <select
              value={resultFilter}
              onChange={(e) => setResultFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Results</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILURE">Failure</option>
              <option value="WARNING">Warning</option>
            </select>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="card">
        <div className="table-container">
          <table className="table">
            <thead className="table-header">
              <tr>
                <th className="table-head">Time</th>
                <th className="table-head">Action</th>
                <th className="table-head">Actor</th>
                <th className="table-head">Entity</th>
                <th className="table-head">Result</th>
                <th className="table-head">Details</th>
              </tr>
            </thead>
            <tbody className="table-body">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-cell text-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <ClipboardList className="h-10 w-10 text-gray-400" />
                      <p className="text-gray-500">No audit entries found</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="table-row">
                    <td className="table-cell">
                      <div className="flex flex-col">
                        <span className="font-mono text-sm">{formatDateTime(log.timestamp)}</span>
                        <span className="text-xs text-gray-500">{formatRelativeTime(log.timestamp)}</span>
                      </div>
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <span className={cn('badge', actionColors[log.action] || 'badge-gray')}>
                          {log.action.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <span className="badge badge-gray">{log.actor_type}</span>
                        <span className="font-mono text-sm">{log.actor_id}</span>
                      </div>
                    </td>
                    <td className="table-cell">
                      {log.entity_type && (
                        <div className="flex flex-col">
                          <span className="text-sm font-medium">{log.entity_type}</span>
                          {log.entity_id && (
                            <span className="text-xs text-gray-500 font-mono">{log.entity_id}</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="table-cell">
                      <span className={cn('badge', resultColors[log.result] || 'badge-gray')}>
                        {log.result}
                      </span>
                    </td>
                    <td className="table-cell">
                      <button
                        onClick={() => showDetails(log)}
                        className="btn-ghost btn-sm p-1.5"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-outline"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="px-4 text-sm text-gray-600 dark:text-gray-400">
            Page {page}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * pageSize >= total}
            className="btn-outline"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}

function showDetails(log: AuditLog) {
  // In a real app, this would open a modal
  console.log('Audit log details:', log)
  alert(
    `Action: ${log.action}\n` +
    `Actor: ${log.actor_type} ${log.actor_id}\n` +
    `Time: ${formatDateTime(log.timestamp)}\n` +
    `Result: ${log.result}\n` +
    `Details: ${JSON.stringify(log.details, null, 2)}`
  )
}

import { CheckCircle } from 'lucide-react'