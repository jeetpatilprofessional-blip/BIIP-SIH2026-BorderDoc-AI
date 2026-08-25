import { ReactNode, useState } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  FileText,
  GitBranch,
  ListChecks,
  ClipboardList,
  Server,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
  Shield,
  AlertTriangle,
} from 'lucide-react'

const navigation = [
  { name: 'Screening', href: '/screening', icon: LayoutDashboard, badge: null },
  { name: 'System Status', href: '/system', icon: Server, badge: null },
  { name: 'Demo Lab', href: '/demo', icon: FlaskConical, badge: null },
]

const caseNavigation = [
  { name: 'Overview', icon: FileText, path: 'overview' },
  { name: 'Identity Graph', icon: GitBranch, path: 'graph' },
  { name: 'Evidence', icon: ListChecks, path: 'evidence' },
  { name: 'Audit Trail', icon: ClipboardList, path: 'audit' },
]

export function Layout({ children }: { children?: ReactNode }) {

  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const isCaseRoute = location.pathname.startsWith('/case/')
  const caseId = isCaseRoute ? location.pathname.split('/')[2] : null

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r bg-white dark:bg-gray-800 transition-all duration-300',
          collapsed ? 'w-16' : 'w-64'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className={cn('flex h-16 items-center justify-between border-b px-4', collapsed && 'justify-center')}>
            <Link to="/screening" className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-primary-600" />
              {!collapsed && (
                <span className="text-xl font-bold text-gray-900 dark:text-white">BIIP</span>
              )}
            </Link>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-1" aria-label="Main navigation">
            {isCaseRoute && caseId && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider px-2">
                  Case {caseId.slice(0, 8)}
                </p>
                <div className="space-y-1 mt-2">
                  {caseNavigation.map((item) => (
                    <Link
                      key={item.name}
                      to={`/case/${caseId}/${item.path}`}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        location.pathname === `/case/${caseId}/${item.path}`
                          ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                          : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                      )}
                    >
                      <item.icon className="h-5 w-5 flex-shrink-0" />
                      {!collapsed && <span>{item.name}</span>}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {!isCaseRoute && (
              <div className="space-y-1">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      location.pathname === item.href
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                    )}
                  >
                    <item.icon className="h-5 w-5 flex-shrink-0" />
                    {!collapsed && <span>{item.name}</span>}
                    {item.badge && !collapsed && (
                      <span className="ml-auto px-2 py-0.5 text-xs bg-primary-100 text-primary-700 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="border-t p-4">
            {!collapsed && (
              <div className="text-xs text-center text-gray-500 dark:text-gray-400">
                BIIP-SIH2026 Prototype v1.0
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main
        className={cn(
          'transition-all duration-300 min-h-screen',
          collapsed ? 'ml-16' : 'ml-64'
        )}
      >
        <div className="p-6 lg:p-8">
          {children || <Outlet />}
        </div>

      </main>
    </div>
  )
}