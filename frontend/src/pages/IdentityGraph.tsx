import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  NodeTypes,
  MarkerType,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { cn, formatRelativeTime, getSeverityColor } from '@/lib/utils'
import { identityGraphApi, casesApi } from '@/lib/api'
import { IdentityGraphSummary } from '@/lib/api'
import {
  ArrowLeft,
  GitBranch,
  RefreshCw,
  AlertTriangle,
  User,
  CreditCard,
  FileText,
  Camera,
  Plane,
  Zap,
  Network,
  Maximize2,
  Download,
} from 'lucide-react'

const nodeIcons: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {

  PERSON: User,
  PASSPORT: CreditCard,
  VISA: FileText,
  NATIONAL_ID: FileText,
  FACE: Camera,
  TRAVEL_EVENT: Plane,
}

const nodeTypeColors: Record<string, string> = {
  PERSON: '#0ea5e9',
  PASSPORT: '#10b981',
  VISA: '#f59e0b',
  NATIONAL_ID: '#8b5cf6',
  FACE: '#ef4444',
  TRAVEL_EVENT: '#6b7280',
}

const edgeTypeColors: Record<string, string> = {
  BELONGS_TO: '#10b981',
  REFERENCES: '#3b82f6',
  MATCHES: '#10b981',
  CONFLICTS_WITH: '#ef4444',
  VALIDATES: '#8b5cf6',
  OCCURRED_BEFORE: '#6b7280',
}

export function IdentityGraph() {
  const { caseId } = useParams<{ caseId: string }>()
  const [graph, setGraph] = useState<IdentityGraphSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)

  const fetchGraph = useCallback(async () => {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      const response = await identityGraphApi.get(caseId)
      if (response.data.nodes.length === 0) {
        // Build graph if not exists
        const buildResponse = await identityGraphApi.build(caseId)
        setGraph(buildResponse.data)
      } else {
        setGraph(response.data)
      }
    } catch (err) {
      setError('Failed to load identity graph')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const { nodes: rfNodes, edges: rfEdges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] }

    // Layout: radial from PERSON node
    const personNode = graph.nodes.find((n) => n.node_type === 'PERSON')
    const layout = new Map<string, { x: number; y: number }>()

    if (personNode) {
      layout.set(personNode.id, { x: 400, y: 300 })
    }

    // Place other nodes in a circle around person
    const others = graph.nodes.filter((n) => n.node_type !== 'PERSON')
    const radius = 250
    others.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(others.length, 1)
      layout.set(node.id, {
        x: 400 + radius * Math.cos(angle),
        y: 300 + radius * Math.sin(angle),
      })
    })

    const nodes: Node[] = graph.nodes.map((n) => ({
      id: n.id,
      type: 'identityNode',
      position: layout.get(n.id) || { x: 0, y: 0 },
      data: {
        label: n.label,
        nodeType: n.node_type,
        properties: n.properties,
        confidence: n.confidence,
        isSelected: selectedNode === n.id,
      },
    }))

    const edges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      type: 'smoothstep',
      label: e.edge_type.replace('_', '\n'),
      animated: e.edge_type === 'CONFLICTS_WITH',
      style: {
        stroke: edgeTypeColors[e.edge_type] || '#94a3b8',
        strokeWidth: e.weight > 0.8 ? 3 : 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edgeTypeColors[e.edge_type] || '#94a3b8',
      },
      data: { isSelected: selectedEdge === e.id },
    }))

    return { nodes, edges }
  }, [graph, selectedNode, selectedEdge])

  const nodeTypes: NodeTypes = useMemo(
    () => ({
      identityNode: IdentityNode,
    }),
    []
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          <p className="text-gray-500">Loading identity graph...</p>
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
          <button onClick={fetchGraph} className="btn-primary mt-4">
            Retry
          </button>
        </div>
      </div>
    )
  }

  const conflictCount = graph?.conflicts.length || 0
  const faceClusterCount = graph?.face_clusters.length || 0

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
              <GitBranch className="h-6 w-6 text-primary-600" />
              Identity Graph
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Cross-document entity resolution and conflict detection
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className="badge badge-gray">{graph?.nodes.length || 0} Nodes</span>
            <span className="badge badge-gray">{graph?.edges.length || 0} Edges</span>
            {conflictCount > 0 && (
              <span className="badge badge-destructive">
                <AlertTriangle className="h-3 w-3 mr-1" />
                {conflictCount} Conflicts
              </span>
            )}
            {faceClusterCount > 1 && (
              <span className="badge badge-warning">
                <Camera className="h-3 w-3 mr-1" />
                {faceClusterCount} Face Clusters
              </span>
            )}
          </div>
          <button onClick={fetchGraph} className="btn-outline" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </button>
          <button className="btn-outline">
            <Download className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Conflicts Alert */}
      {conflictCount > 0 && (
        <div className="card border-red-200 dark:border-red-800">
          <div className="card-header">
            <h2 className="card-title text-red-700 dark:text-red-300 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Identity Conflicts Detected
            </h2>
          </div>
          <div className="card-content space-y-3">
            {graph?.conflicts.map((conflict, i) => (
              <div key={i} className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-red-800 dark:text-red-200">
                    {conflict.field} Mismatch
                  </span>
                  <span className={cn('badge', getSeverityColor(conflict.severity))}>
                    {conflict.severity}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Passport Value</p>
                    <p className="font-mono font-medium">{conflict.passport_value}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Visa Value</p>
                    <p className="font-mono font-medium">{conflict.visa_value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Face Clusters */}
      {faceClusterCount > 1 && (
        <div className="card border-yellow-200 dark:border-yellow-800">
          <div className="card-header">
            <h2 className="card-title text-yellow-700 dark:text-yellow-300 flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Face Identity Clusters
            </h2>
          </div>
          <div className="card-content">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              Multiple distinct faces detected for this person. Possible identity fragmentation.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {graph?.face_clusters.map((cluster) => (
                <div key={cluster.cluster_id} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="font-medium text-sm">{cluster.cluster_id}</p>
                  <p className="text-xs text-gray-500">
                    {cluster.faces.length} faces • {(cluster.avg_similarity * 100).toFixed(0)}% similarity
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      <div className="card overflow-hidden">
        <div className="h-[600px] w-full bg-gray-50 dark:bg-gray-900">
          {graph && graph.nodes.length > 0 ? (
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) => nodeTypeColors[(n.data as any).nodeType] || '#94a3b8'}
                maskColor="rgba(0,0,0,0.1)"
              />
            </ReactFlow>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <Network className="h-16 w-16 text-gray-400 mb-4" />
              <p className="text-gray-500">No graph data available</p>
              <p className="text-sm text-gray-400">Upload documents to build identity graph</p>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="card">
        <div className="card-content">
          <h3 className="font-medium mb-3">Legend</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-500 mb-2">Node Types</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(nodeTypeColors).map(([type, color]) => {
                  const Icon = nodeIcons[type] || FileText
                  return (
                    <span key={type} className="badge badge-gray flex items-center gap-1">
                      <Icon className="h-3 w-3" style={{ color }} />
                      {type}
                    </span>
                  )
                })}
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-2">Edge Types</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(edgeTypeColors).map(([type, color]) => (
                  <span key={type} className="badge badge-gray flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                    {type.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface IdentityNodeData {
  label: string
  nodeType: string
  properties: Record<string, any>
  confidence: number
  isSelected: boolean
}

function IdentityNode({ data }: { data: IdentityNodeData }) {
  const Icon = nodeIcons[data.nodeType] || FileText
  const color = nodeTypeColors[data.nodeType] || '#94a3b8'

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 shadow-sm min-w-[160px] bg-white dark:bg-gray-800',
        data.isSelected ? 'border-primary-500 ring-2 ring-primary-200' : 'border-gray-200 dark:border-gray-700'
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="p-1.5 rounded" style={{ backgroundColor: `${color}20` }}>
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400">
        {data.nodeType}
        {data.confidence > 0 && ` • ${(data.confidence * 100).toFixed(0)}% conf`}
      </div>
      {Object.keys(data.properties).length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
          {Object.entries(data.properties)
            .slice(0, 3)
            .map(([key, value]) => (
              <p key={key} className="text-xs text-gray-600 dark:text-gray-300">
                {key}: <span className="font-mono">{String(value).slice(0, 20)}</span>
              </p>
            ))}
        </div>
      )}
    </div>
  )
}