import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { parseApiError } from './utils'

// Types
export interface Case {
  id: string
  case_number: string
  status: string
  officer_id: string
  location: string
  checkpoint_type: string
  priority: number
  created_at: string
  updated_at: string
  closed_at?: string
  person_id?: string
}

export interface Document {
  id: string
  case_id: string
  document_type: string
  document_subtype?: string
  country_code?: string
  document_number?: string
  mrz_raw?: string
  mrz_valid?: boolean
  barcode_raw?: string
  barcode_data?: Record<string, any>
  image_path_front?: string
  image_path_back?: string
  image_path_photo?: string
  processing_status: string
  created_at: string
  updated_at: string
}

export interface DocumentField {
  id: string
  document_id: string
  field_name: string
  value: string
  confidence: number
  source: string
  bounding_box?: Record<string, number>
  matched_field_id?: string
  is_valid?: boolean
  validation_error?: string
}

export interface FaceResult {
  id: string
  case_id: string
  document_id?: string
  source_type: string
  image_path: string
  embedding?: number[]
  quality_score?: number
  match_score?: number
  match_result?: string
  compared_to_document_id?: string
  liveness_result?: string
  liveness_confidence?: number
  liveness_details?: Record<string, any>
  created_at: string
}

export interface TamperResult {
  id: string
  document_id: string
  tampered: boolean
  confidence: number
  reasons?: string
  cross_field_consistency?: string
  image_analysis?: string
  photo_consistency?: string
  regions?: string
  created_at: string
}

export interface EvidenceAtom {
  id: string
  case_id: string
  evidence_type: string
  source: string
  severity: string
  confidence: number
  description: string
  explanation?: string
  entities?: string
  freshness: string
  last_synced_at?: string
  freshness_policy_hours?: number
  rule_or_model_version?: string
  created_at: string
}

export interface FusionResult {
  case_id: string
  recommendation: string
  confidence: number
  reasoning: string
  primary_reasons: string[]
  supporting_evidence: EvidenceContribution[]
  contradicting_evidence: EvidenceContribution[]
  data_freshness_warnings: string[]
  stale_evidence_count: number
  unavailable_evidence_count: number
  adverse_evidence_count: number
  limitations: string[]
  recommended_action: string
  evidence_atoms_considered: number
  positive_score: number
  negative_score: number
  net_score: number
}

export interface EvidenceContribution {
  evidence_id: string
  evidence_type: string
  source: string
  severity: string
  confidence: number
  description: string
  explanation?: string
  entities: string[]
  freshness: string
  weight: number
  contribution: number
}

export interface FreshnessCheckResult {
  source: string
  status_type: string
  entity_identifier: string
  state: string
  last_synced_at?: string
  hours_since_sync?: number
  policy_hours: number
  is_stale: boolean
  is_unavailable: boolean
  is_adverse: boolean
  details: Record<string, any>
  explanation: string
  display_status: string
  display_color: string
}

export interface IdentityGraphNode {
  id: string
  node_type: string
  label: string
  properties: Record<string, any>
  confidence: number
}

export interface IdentityGraphEdge {
  id: string
  source_node_id: string
  target_node_id: string
  edge_type: string
  weight: number
  properties: Record<string, any>
}

export interface IdentityGraphSummary {
  nodes: IdentityGraphNode[]
  edges: IdentityGraphEdge[]
  conflicts: Conflict[]
  face_clusters: FaceCluster[]
}

export interface Conflict {
  field: string
  passport_value: string
  visa_value: string
  severity: string
  edges: string[]
}

export interface FaceCluster {
  cluster_id: string
  faces: string[]
  representative_face: string
  avg_similarity: number
}

export interface AuditLog {
  id: string
  timestamp: string
  action: string
  actor_id: string
  actor_type: string
  case_id?: string
  entity_type?: string
  entity_id?: string
  result: string
  details: Record<string, any>
  ip_address?: string
  user_agent?: string
  correlation_id?: string
  previous_hash: string
  hash: string
}

export interface SyncQueueItem {
  id: string
  case_id?: string
  operation_type: string
  payload: Record<string, any>
  priority: string
  status: string
  created_at: string
  started_at?: string
  completed_at?: string
  retry_count: number
  max_retries: number
  last_error?: string
  idempotency_key?: string
}

export interface SystemStatus {
  connectivity: {
    is_online: boolean
    last_successful_sync?: string
    pending_queue_size: number
    failed_queue_size: number
    estimated_backlog_hours: number
    central_endpoint: string
    last_check: string
  }
  freshness: {
    overall_state: string
    fresh_count: number
    stale_count: number
    unavailable_count: number
    adverse_count: number
    total_checks: number
  }
  services: {
    ocr: boolean
    face_verification: boolean
    tamper_detection: boolean
    liveness: boolean
    rules_engine: boolean
    central_connectivity: boolean
  }
}

export interface DemoScenario {
  id: string
  name: string
  description: string
  expected_recommendation: string
  documents: string[]
  face_scenario: string
}

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor for auth
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API functions
export const casesApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get<{ cases: Case[]; total: number }>('/cases', { params }),

  get: (id: string) =>
    api.get<Case>(`/cases/${id}`),

  create: (data: { location: string; checkpoint_type: string; officer_id: string }) =>
    api.post<Case>('/cases', data),

  update: (id: string, data: Partial<Case>) =>
    api.patch<Case>(`/cases/${id}`, data),

  close: (id: string, data: { final_decision: string; rationale: string }) =>
    api.post<Case>(`/cases/${id}/close`, data),
}

export const documentsApi = {
  list: (caseId: string) =>
    api.get<Document[]>(`/cases/${caseId}/documents`),

  get: (caseId: string, documentId: string) =>
    api.get<Document>(`/cases/${caseId}/documents/${documentId}`),

  upload: (caseId: string, file: File, documentType: string, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', documentType)
    return api.post<Document>(`/cases/${caseId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total))
        }
      },
    })
  },

  process: (caseId: string, documentId: string) =>
    api.post<Document>(`/cases/${caseId}/documents/${documentId}/process`),

  getFields: (caseId: string, documentId: string) =>
    api.get<DocumentField[]>(`/cases/${caseId}/documents/${documentId}/fields`),

  delete: (caseId: string, documentId: string) =>
    api.delete(`/cases/${caseId}/documents/${documentId}`),
}

export const faceApi = {
  capture: (caseId: string, file: File, documentId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (documentId) formData.append('document_id', documentId)
    return api.post<FaceResult>(`/cases/${caseId}/face/capture`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  verify: (caseId: string, faceId: string, documentId: string) =>
    api.post<FaceResult>(`/cases/${caseId}/face/verify`, { face_id: faceId, document_id: documentId }),

  liveness: (caseId: string, faceId: string, challengeType: 'blink' | 'turn_left' | 'turn_right' | 'nod') =>
    api.post<FaceResult>(`/cases/${caseId}/face/liveness`, { face_id: faceId, challenge_type: challengeType }),

  list: (caseId: string) =>
    api.get<FaceResult[]>(`/cases/${caseId}/face`),
}

export const tamperApi = {
  analyze: (caseId: string, documentId: string) =>
    api.post<TamperResult>(`/cases/${caseId}/documents/${documentId}/tamper`),

  get: (caseId: string, documentId: string) =>
    api.get<TamperResult>(`/cases/${caseId}/documents/${documentId}/tamper`),
}

export const evidenceApi = {
  generate: (caseId: string) =>
    api.post<EvidenceAtom[]>(`/cases/${caseId}/evidence/generate`),

  list: (caseId: string) =>
    api.get<EvidenceAtom[]>(`/cases/${caseId}/evidence`),

  getFusion: (caseId: string) =>
    api.get<FusionResult>(`/cases/${caseId}/evidence/fusion`),
}

export const identityGraphApi = {
  build: (caseId: string) =>
    api.post<IdentityGraphSummary>(`/cases/${caseId}/graph/build`),

  get: (caseId: string) =>
    api.get<IdentityGraphSummary>(`/cases/${caseId}/graph`),
}

export const auditApi = {
  list: (params?: { case_id?: string; actor_id?: string; action?: string; limit?: number }) =>
    api.get<AuditLog[]>('/audit', { params }),

  getCaseTrail: (caseId: string, limit?: number) =>
    api.get<AuditLog[]>(`/audit/case/${caseId}`, { params: { limit } }),

  verifyChain: (caseId?: string) =>
    api.get<{ total_entries: number; broken_links: number; intact: boolean }>('/audit/verify', {
      params: { case_id: caseId },
    }),
}

export const syncApi = {
  getQueue: () =>
    api.get<SyncQueueItem[]>('/sync/queue'),

  process: (batchSize?: number) =>
    api.post<{ results: any[] }>('/sync/process', { batch_size: batchSize }),

  getStatus: () =>
    api.get<SystemStatus>('/sync/status'),

  triggerStatusCheck: (caseId: string, statusType: string, entityIdentifier: string) =>
    api.post(`/cases/${caseId}/sync/status-check`, { status_type: statusType, entity_identifier: entityIdentifier }),

  retryFailed: () =>
    api.post('/sync/retry-failed'),
}

export const systemApi = {
  health: () =>
    api.get<{ status: string; version: string; services: Record<string, boolean> }>('/health'),

  getStatus: () =>
    api.get<SystemStatus>('/system/status'),

  getConfig: () =>
    api.get<Record<string, any>>('/system/config'),
}

export const demoApi = {
  getScenarios: () =>
    api.get<DemoScenario[]>('/demo/scenarios'),

  runScenario: (scenarioId: string) =>
    api.post<{ case_id: string }>(`/demo/scenarios/${scenarioId}/run`),

  loadTestData: () =>
    api.post('/demo/load-test-data'),
}

export default api