import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { cn, formatDateTime, getRecommendationColor, formatRelativeTime } from '@/lib/utils'
import { casesApi } from '@/lib/api'
import { Case } from '@/lib/api'
import {
  Plus,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  HelpCircle,
  MoreVertical,
  RefreshCw,
  FileText,

} from 'lucide-react'

const statusColors: Record<string, string> = {
  OPEN: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  PENDING_REVIEW: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  CLOSED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  ESCALATED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const priorityColors: Record<number, string> = {
  1: 'bg-gray-100 text-gray-800',
  2: 'bg-blue-100 text-blue-800',
  3: 'bg-yellow-100 text-yellow-800',
  4: 'bg-orange-100 text-orange-800',
  5: 'bg-red-100 text-red-800',
}

export function Screening() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({
    key: 'created_at',
    direction: 'desc',
  })

  const fetchCases = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await casesApi.list({ limit: 50 })
      setCases(response.data.cases)
    } catch (err) {
      setError(parseApiError(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCases()
  }, [])

  const handleSort = (key: string) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const sortedCases = [...cases].sort((a, b) => {
    const aVal = a[sortConfig.key as keyof Case]
    const bVal = b[sortConfig.key as keyof Case]
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
    return 0
  })

  const filteredCases = sortedCases.filter((c) => {
    const matchesSearch =
      c.case_number.toLowerCase().includes(search.toLowerCase()) ||
      c.location.toLowerCase().includes(search.toLowerCase()) ||
      (c.person_id?.toLowerCase().includes(search.toLowerCase()) ?? false)
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const statuses = ['OPEN', 'IN_PROGRESS', 'PENDING_REVIEW', 'CLOSED', 'ESCALATED']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Screening Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage and review border identity cases
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchCases}
            disabled={loading}
            className="btn-outline flex items-center gap-2"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            Refresh
          </button>
          <Link to="/demo" className="btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            New Case
          </Link>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-red-700 dark:text-red-300 flex-1">{error}</p>
          <button onClick={fetchCases} className="btn-sm btn-outline">
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-content flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search cases..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-500 dark:text-gray-400">Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Cases Table */}
      <div className="card">
        <div className="table-container">
          <table className="table">
            <thead className="table-header">
              <tr>
                <th className="table-head cursor-pointer" onClick={() => handleSort('case_number')}>
                  Case Number
                  {sortConfig.key === 'case_number' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>
                <th className="table-head cursor-pointer" onClick={() => handleSort('status')}>
                  Status
                  {sortConfig.key === 'status' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>
                <th className="table-head cursor-pointer" onClick={() => handleSort('priority')}>
                  Priority
                  {sortConfig.key === 'priority' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>
                <th className="table-head cursor-pointer" onClick={() => handleSort('location')}>
                  Location
                  {sortConfig.key === 'location' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>
                <th className="table-head cursor-pointer" onClick={() => handleSort('checkpoint_type')}>
                  Checkpoint
                  {sortConfig.key === 'checkpoint_type' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>
                <th className="table-head cursor-pointer" onClick={() => handleSort('created_at')}>
                  Created
                  {sortConfig.key === 'created_at' && (
                    <span className="ml-1">{sortConfig.direction === 'asc' ? <ChevronUp className="h-4 w-4 inline" /> : <ChevronDown className="h-4 w-4 inline" />}</span>
                  )}
                </th>

                <th className="table-head">Actions</th>
              </tr>
            </thead>
            <tbody className="table-body">
              {loading ? (
                <tr>
                  <td colSpan={8} className="table-cell text-center py-8">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="h-5 w-5 animate-spin text-primary-600" />
                      <span className="text-gray-500">Loading cases...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="table-cell text-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <HelpCircle className="h-10 w-10 text-gray-400" />
                      <p className="text-gray-500">No cases found</p>
                      <p className="text-sm text-gray-400">
                        {search || statusFilter !== 'all'
                          ? 'Try adjusting your filters'
                          : 'Create a new case from the Demo Lab'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredCases.map((c) => (
                  <tr key={c.id} className="table-row">
                    <td className="table-cell font-mono font-medium">{c.case_number}</td>
                    <td className="table-cell">
                      <span className={cn('badge', statusColors[c.status] || 'badge-gray')}>
                        {c.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className={cn('badge', priorityColors[c.priority] || 'badge-gray')}>
                        P{c.priority}
                      </span>
                    </td>
                    <td className="table-cell">{c.location}</td>
                    <td className="table-cell">{c.checkpoint_type}</td>
                    <td className="table-cell text-gray-500 dark:text-gray-400">
                      {formatRelativeTime(c.created_at)}
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/case/${c.id}`}
                          className="btn-ghost btn-sm p-1.5"
                          title="View case"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </Link>
                        <button className="btn-ghost btn-sm p-1.5" title="More actions">
                          <MoreVertical className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Cases"
          value={cases.length}
          icon={FileText}
          color="blue"
        />
        <StatCard
          title="Open"
          value={cases.filter((c) => c.status === 'OPEN').length}
          icon={Clock}
          color="blue"
        />
        <StatCard
          title="In Progress"
          value={cases.filter((c) => c.status === 'IN_PROGRESS').length}
          icon={AlertTriangle}
          color="yellow"
        />
        <StatCard
          title="Closed"
          value={cases.filter((c) => c.status === 'CLOSED').length}
          icon={CheckCircle}
          color="green"
        />
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  color: string
}) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
        </div>
        <div className={cn('p-3 rounded-lg', colorMap[color])}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}

function parseApiError(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return 'An unknown error occurred'
}