import { useState, useEffect, useCallback } from 'react'
import { cn, formatRelativeTime } from '@/lib/utils'
import { syncApi, systemApi, casesApi } from '@/lib/api'
import type { SystemStatus, SyncQueueItem } from '@/lib/api'

import {
  Server,
  Database,
  Cpu,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Shield,
  Zap,
  Eye,
  Settings,
  Activity,
  HardDrive,
  Network,
} from 'lucide-react'

const serviceIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  ocr: Eye,
  face_verification: Shield,
  tamper_detection: AlertTriangle,
  liveness: Zap,
  rules_engine: Settings,
  central_connectivity: Network,
}

export function SystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [queue, setQueue] = useState<SyncQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statusRes, queueRes] = await Promise.all([
        systemApi.getStatus().catch(() => ({ data: null })),
        syncApi.getQueue().catch(() => ({ data: [] })),
      ])
      setStatus(statusRes.data)
      setQueue(queueRes.data)
    } catch (err) {
      setError('Failed to load system status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleProcessQueue = async () => {
    setProcessing(true)
    try {
      await syncApi.process(20)
      await fetchStatus()
    } catch (err) {
      setError('Failed to process queue')
    } finally {
      setProcessing(false)
    }
  }

  const handleRetryFailed = async () => {
    try {
      await syncApi.retryFailed()
      await fetchStatus()
    } catch (err) {
      setError('Failed to retry')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading system status...</p>
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
            <Server className="h-6 w-6 text-primary-600" />
            System Status
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Real-time system health, connectivity, and sync monitoring
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchStatus} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button onClick={handleProcessQueue} className="btn-primary" disabled={processing}>
            {processing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Activity className="h-4 w-4 mr-2" />
                Process Queue
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

      {/* Connectivity Status */}
      {status?.connectivity && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <Network className="h-5 w-5" />
              Connectivity
            </h2>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatusCard
                title="Central Connection"
                value={status.connectivity.is_online ? 'Online' : 'Offline'}
                icon={status.connectivity.is_online ? Wifi : WifiOff}
                color={status.connectivity.is_online ? 'green' : 'red'}
                subtitle={status.connectivity.last_successful_sync
                  ? `Last sync: ${formatRelativeTime(status.connectivity.last_successful_sync)}`
                  : 'Never synced'}
              />
              <StatusCard
                title="Pending Queue"
                value={status.connectivity.pending_queue_size.toString()}
                icon={Activity}
                color="blue"
                subtitle={`${status.connectivity.estimated_backlog_hours.toFixed(1)}h estimated backlog`}
              />
              <StatusCard
                title="Failed Items"
                value={status.connectivity.failed_queue_size.toString()}
                icon={XCircle}
                color={status.connectivity.failed_queue_size > 0 ? 'red' : 'green'}
                subtitle={status.connectivity.failed_queue_size > 0 ? 'Click retry to re-process' : 'All clear'}
              />
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-500">
                Endpoint: <span className="font-mono text-gray-900 dark:text-white">{status.connectivity.central_endpoint}</span>
              </p>
              <p className="text-sm text-gray-500">
                Last checked: {formatRelativeTime(status.connectivity.last_check)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Freshness Status */}
      {status?.freshness && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Data Freshness
            </h2>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
              <FreshnessCard
                title="Fresh"
                count={status.freshness.fresh_count}
                color="green"
                icon={CheckCircle}
              />
              <FreshnessCard
                title="Stale"
                count={status.freshness.stale_count}
                color="orange"
                icon={AlertTriangle}
              />
              <FreshnessCard
                title="Unavailable"
                count={status.freshness.unavailable_count}
                color="red"
                icon={WifiOff}
              />
              <FreshnessCard
                title="Adverse"
                count={status.freshness.adverse_count}
                color="red"
                icon={XCircle}
              />
              <FreshnessCard
                title="Total Checks"
                count={status.freshness.total_checks}
                color="blue"
                icon={Activity}
              />
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="font-medium">Overall State: </p>
              <span className={cn('badge px-3 py-1 text-base ml-2', freshnessOverallColor(status.freshness.overall_state))}>
                {status.freshness.overall_state.replace('_', ' ')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Service Health */}
      {status?.services && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              Service Health
            </h2>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Object.entries(status.services).map(([key, healthy]) => (
                <ServiceCard
                  key={key}
                  name={key.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  healthy={healthy}
                  icon={serviceIcons[key] || Settings}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sync Queue */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="card-title flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Sync Queue ({queue.length})
          </h2>
          <div className="flex items-center gap-2">
            {status?.connectivity?.failed_queue_size && status.connectivity.failed_queue_size > 0 && (
              <button onClick={handleRetryFailed} className="btn-sm btn-outline">
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry Failed
              </button>
            )}
          </div>
        </div>
        <div className="card-content">
          {queue.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
              <p>Sync queue is empty</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead className="table-header">
                  <tr>
                    <th className="table-head">Operation</th>
                    <th className="table-head">Case</th>
                    <th className="table-head">Priority</th>
                    <th className="table-head">Status</th>
                    <th className="table-head">Created</th>
                    <th className="table-head">Retries</th>
                    <th className="table-head">Error</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {queue.map((item) => (
                    <tr key={item.id} className="table-row">
                      <td className="table-cell">
                        <span className="badge badge-gray">{item.operation_type.replace('_', ' ')}</span>
                      </td>
                      <td className="table-cell font-mono text-sm">
                        {item.case_id?.slice(0, 8) || 'N/A'}
                      </td>
                      <td className="table-cell">
                        <span className={cn('badge', priorityColor(item.priority))}>
                          {item.priority}
                        </span>
                      </td>
                      <td className="table-cell">
                        <span className={cn('badge', queueStatusColor(item.status))}>
                          {item.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="table-cell text-sm text-gray-500">
                        {formatRelativeTime(item.created_at)}
                      </td>
                      <td className="table-cell">
                        <span className="badge badge-gray">{item.retry_count}/{item.max_retries}</span>
                      </td>
                      <td className="table-cell">
                        {item.last_error && (
                          <span className="text-sm text-red-600 dark:text-red-400 truncate max-w-xs block" title={item.last_error}>
                            {item.last_error}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Quick Actions</h2>
        </div>
        <div className="card-content grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionButton
            label="Full Health Check"
            description="Run comprehensive system diagnostics"
            icon={Activity}
            onClick={fetchStatus}
          />
          <ActionButton
            label="Force Sync All"
            description="Trigger immediate sync for all pending cases"
            icon={Network}
            onClick={handleProcessQueue}
          />
          <ActionButton
            label="Clear Failed Queue"
            description="Remove permanently failed sync items"
            icon={XCircle}
            onClick={handleRetryFailed}
            variant="destructive"
          />
        </div>
      </div>
    </div>
  )
}

function StatusCard({
  title,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  subtitle?: string
}) {
  const colorMap: Record<string, string> = {
    green: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
    red: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
    orange: 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
    yellow: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  }

  return (
    <div className="p-4 rounded-lg border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className={cn('p-3 rounded-lg', colorMap[color])}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}

function FreshnessCard({
  title,
  count,
  color,
  icon: Icon,
}: {
  title: string
  count: number
  color: string
  icon: React.ComponentType<{ className?: string }>
}) {
  const colorMap: Record<string, string> = {
    green: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
    red: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
    orange: 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
    yellow: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  }

  return (
    <div className="text-center p-4">
      <div className={cn('p-3 rounded-lg inline-flex', colorMap[color])}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{count}</p>
      <p className="text-sm text-gray-500">{title}</p>
    </div>
  )
}

function ServiceCard({
  name,
  healthy,
  icon: Icon,
}: {
  name: string
  healthy: boolean
  icon: React.ComponentType<{ className?: string }>
}) {
  return (
    <div className={cn('p-4 rounded-lg text-center', healthy ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20')}>
      <div className={cn('p-2 rounded-lg inline-flex mb-2', healthy ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30')}>
        <Icon className={cn('h-5 w-5', healthy ? 'text-green-600' : 'text-red-600')} />
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-white">{name}</p>
      <span className={cn('badge mt-2', healthy ? 'badge-success' : 'badge-destructive')}>
        {healthy ? 'Healthy' : 'Degraded'}
      </span>
    </div>
  )
}

function ActionButton({
  label,
  description,
  icon: Icon,
  onClick,
  variant = 'primary',
}: {
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  onClick: () => void
  variant?: 'primary' | 'destructive'
}) {
  const variantClasses = variant === 'destructive'
    ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/30'
    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'

  return (
    <button
      onClick={onClick}
      className={cn('p-4 rounded-lg border text-left transition-colors', variantClasses)}
    >
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">{label}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{description}</p>
        </div>
      </div>
    </button>
  )
}

function freshnessOverallColor(state: string): string {
  switch (state) {
    case 'VERIFIED_FRESH':
      return 'badge-success'
    case 'VERIFIED_STALE':
      return 'badge-warning'
    case 'UNAVAILABLE':
      return 'badge-destructive'
    case 'CONFIRMED_ADVERSE':
      return 'badge-destructive'
    default:
      return 'badge-gray'
  }
}

function priorityColor(priority: string): string {
  switch (priority) {
    case 'CRITICAL':
      return 'badge-destructive'
    case 'HIGH':
      return 'badge-warning'
    case 'NORMAL':
      return 'badge-info'
    case 'LOW':
      return 'badge-gray'
    default:
      return 'badge-gray'
  }
}

function queueStatusColor(status: string): string {
  switch (status) {
    case 'PENDING':
      return 'badge-gray'
    case 'IN_PROGRESS':
      return 'badge-info'
    case 'COMPLETED':
      return 'badge-success'
    case 'FAILED':
      return 'badge-destructive'
    case 'PARTIAL':
      return 'badge-warning'
    default:
      return 'badge-gray'
  }
}