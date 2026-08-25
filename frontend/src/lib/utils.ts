import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelativeTime(date: string | Date): string {
  const d = new Date(date)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(d)
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-200'
    case 'high':
      return 'text-orange-700 bg-orange-100 dark:bg-orange-900 dark:text-orange-200'
    case 'medium':
      return 'text-yellow-700 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200'
    case 'low':
      return 'text-blue-700 bg-blue-100 dark:bg-blue-900 dark:text-blue-200'
    case 'info':
      return 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
    default:
      return 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
  }
}

export function getRecommendationColor(recommendation: string): string {
  switch (recommendation) {
    case 'LOW_CONCERN':
      return 'text-green-700 bg-green-100 dark:bg-green-900 dark:text-green-200'
    case 'SECONDARY_INSPECTION':
      return 'text-yellow-700 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200'
    case 'HIGH_CONCERN':
      return 'text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-200'
    case 'INSUFFICIENT_EVIDENCE':
      return 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
    default:
      return 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
  }
}

export function getFreshnessColor(state: string): string {
  switch (state) {
    case 'VERIFIED_FRESH':
      return 'text-green-700 bg-green-100 dark:bg-green-900 dark:text-green-200'
    case 'VERIFIED_STALE':
      return 'text-orange-700 bg-orange-100 dark:bg-orange-900 dark:text-orange-200'
    case 'UNAVAILABLE':
      return 'text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-200'
    case 'CONFIRMED_ADVERSE':
      return 'text-red-900 bg-red-200 dark:bg-red-900 dark:text-red-100'
    default:
      return 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
  }
}

export function getFreshnessLabel(state: string): string {
  switch (state) {
    case 'VERIFIED_FRESH':
      return 'Fresh'
    case 'VERIFIED_STALE':
      return 'Stale'
    case 'UNAVAILABLE':
      return 'Unavailable'
    case 'CONFIRMED_ADVERSE':
      return 'Adverse'
    default:
      return state
  }
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

export function parseApiError(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return 'An unknown error occurred'
}