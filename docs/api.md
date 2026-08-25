# BIIP-SIH2026 API Reference

**Base URL**: `http://localhost:8000/api` (development)  
**Content-Type**: `application/json`  
**Authentication**: Bearer token (future) / API Key (future)

---

## Health & System

### GET `/health`
Liveness probe - returns 200 if service is running.

**Response**: `{"status": "ok"}`

### GET `/health/ready`
Readiness probe - returns 200 if DB and critical services are ready.

**Response**: `{"status": "ready", "checks": {"database": "ok", "models": "loaded"}}`

### GET `/system/status`
System status including model load state, queue depths, sync status.

**Response**:
```json
{
  "status": "operational",
  "models": {
    "ocr": "loaded",
    "face": "loaded",
    "liveness": "loaded"
  },
  "sync_queue": {
    "pending": 3,
    "processing": 1,
    "failed": 0
  },
  "central_connectivity": "online"
}
```

---

## Cases

### POST `/cases`
Create a new screening case.

**Request**:
```json
{
  "case_number": "BIIP-2026-001",
  "location": "DEL-IMM-01",
  "officer_id": "OFC-123",
  "notes": "Routine screening"
}
```

**Response** (201):
```json
{
  "id": "uuid",
  "case_number": "BIIP-2026-001",
  "location": "DEL-IMM-01",
  "officer_id": "OFC-123",
  "status": "OPEN",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

### GET `/cases`
List cases with pagination and filters.

**Query Parameters**:
- `page` (default: 1)
- `page_size` (default: 20, max: 100)
- `status` (OPEN, IN_PROGRESS, CLOSED)
- `officer_id`
- `date_from`, `date_to`

**Response**:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### GET `/cases/{case_id}`
Get case details with summary.

### PATCH `/cases/{case_id}`
Update case (status, officer assignment, notes).

### DELETE `/cases/{case_id}`
Delete case (soft delete - marks CLOSED).

---

## Documents

### POST `/cases/{case_id}/documents`
Upload a document for processing.

**Request** (multipart/form-data):
- `file`: Image file (JPG, PNG, PDF)
- `document_type`: PASSPORT | VISA | NATIONAL_ID
- `country_code`: ISO 3166-1 alpha-3 (e.g., "IND")
- `side`: FRONT | BACK (for national ID)

**Response** (202):
```json
{
  "document_id": "uuid",
  "status": "PROCESSING",
  "message": "Document queued for processing"
}
```

### GET `/cases/{case_id}/documents`
List documents for a case.

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "document_type": "PASSPORT",
      "country_code": "IND",
      "document_number": "P<IND12345678",
      "processing_status": "COMPLETED",
      "created_at": "2026-01-15T10:30:00Z"
    }
  ]
}
```

### GET `/documents/{document_id}`
Get document with extracted fields.

### GET `/documents/{document_id}/fields`
Get extracted document fields.

**Response**:
```json
{
  "fields": [
    {"field_name": "surname", "value": "DEMO", "confidence": 0.95, "source": "OCR"},
    {"field_name": "birth_date", "value": "1990-01-15", "confidence": 0.98, "source": "MRZ"}
  ]
}
```

### GET `/documents/{document_id}/mrz`
Get parsed MRZ data.

### GET `/documents/{document_id}/barcode`
Get parsed barcode data.

### GET `/documents/{document_id}/tamper`
Get tamper detection results.

**Response**:
```json
{
  "tamper_detected": false,
  "anomaly_score": 0.02,
  "regions": [
    {"region": "photo", "anomaly_score": 0.01, "details": {}},
    {"region": "mrz", "anomaly_score": 0.03, "details": {}}
  ],
  "evidence_atoms": [...]
}
```

---

## Face Verification

### POST `/cases/{case_id}/face/verify`
Submit live face capture for verification against document.

**Request** (multipart/form-data):
- `file`: Live face image
- `document_id`: Document to compare against
- `challenge_response`: Optional (blink/turn data)

**Response** (202):
```json
{
  "face_result_id": "uuid",
  "status": "PROCESSING"
}
```

### GET `/face-results/{face_result_id}`
Get face verification result.

**Response**:
```json
{
  "id": "uuid",
  "match_score": 0.92,
  "match_result": "MATCH",
  "liveness_result": "LIVE",
  "liveness_confidence": 0.88,
  "compared_to_document_id": "uuid",
  "evidence_atoms": [...]
}
```

---

## Evidence & Fusion

### GET `/evidence/{case_id}`
Get all evidence atoms for a case.

**Response**:
```json
{
  "atoms": [
    {
      "id": "uuid",
      "evidence_type": "FACE_MATCH",
      "severity": "LOW",
      "source": "FACE_VERIFICATION",
      "confidence": 0.92,
      "description": "Live face matches passport photo (0.92)",
      "freshness": "VERIFIED_FRESH",
      "details": {"match_score": 0.92, "liveness": "LIVE"}
    }
  ],
  "summary": {
    "total": 15,
    "positive": 12,
    "negative": 3,
    "by_severity": {"INFO": 3, "LOW": 6, "MEDIUM": 4, "HIGH": 2, "CRITICAL": 0},
    "by_freshness": {"VERIFIED_FRESH": 10, "VERIFIED_STALE": 2, "UNAVAILABLE": 3}
  }
}
```

### GET `/evidence/{case_id}/fusion`
Get fusion result and recommendation.

**Response**:
```json
{
  "case_id": "uuid",
  "recommendation": "LOW_CONCERN",
  "confidence": 0.87,
  "positive_score": 0.82,
  "negative_score": 0.08,
  "net_score": 0.74,
  "contributing_atoms": [
    {"evidence_type": "DOCUMENT_VALID", "contribution": 0.15, "freshness": "VERIFIED_FRESH"},
    {"evidence_type": "FACE_MATCH", "contribution": 0.18, "freshness": "VERIFIED_FRESH"},
    {"evidence_type": "WATCHLIST_CLEAN", "contribution": 0.12, "freshness": "VERIFIED_FRESH"}
  ],
  "freshness_breakdown": {
    "VERIFIED_FRESH": 10,
    "VERIFIED_STALE": 1,
    "UNAVAILABLE": 2,
    "CONFIRMED_ADVERSE": 0
  },
  "generated_at": "2026-01-15T10:35:00Z"
}
```

### POST `/evidence/{case_id}/regenerate`
Regenerate evidence atoms and fusion (after sync completes).

---

## Identity Graph

### GET `/identity-graph/{case_id}`
Get identity graph for visualization.

**Response**:
```json
{
  "nodes": [
    {"id": "n1", "type": "PERSON", "label": "DEMO TRAVELER", "attributes": {...}, "confidence": 0.95},
    {"id": "n2", "type": "DOCUMENT", "label": "PASSPORT P<IND12345678", "attributes": {...}}
  ],
  "edges": [
    {"id": "e1", "source": "n2", "target": "n1", "type": "BELONGS_TO", "confidence": 0.95},
    {"id": "e2", "source": "n3", "target": "n2", "type": "VALIDATES", "confidence": 0.9}
  ],
  "conflicts": [
    {"edge_id": "e5", "field": "birth_date", "values": ["1990-01-15", "1991-01-15"], "severity": "HIGH"}
  ]
}
```

### GET `/identity-graph/{case_id}/conflicts`
Get only conflict edges.

---

## Recommendations & Officer Actions

### GET `/recommendations/{case_id}`
Get current recommendation with full explanation.

**Response**:
```json
{
  "case_id": "uuid",
  "recommendation": "SECONDARY_INSPECTION",
  "confidence": 0.72,
  "reasoning": [
    "Passport valid (VERIFIED_FRESH)",
    "Face match strong (0.92, VERIFIED_FRESH)",
    "Watchlist check UNAVAILABLE (offline) - cannot confirm clean status",
    "Visa valid (VERIFIED_FRESH)"
  ],
  "critical_flags": [],
  "evidence_summary": {...},
  "officer_actions": [
    {"action": "ALLOW", "requires_supervisor": false},
    {"action": "SECONDARY_INSPECTION", "requires_supervisor": false},
    {"action": "DENY", "requires_supervisor": true},
    {"action": "DETAIN", "requires_supervisor": true}
  ]
}
```

### POST `/officer-actions`
Record officer decision.

**Request**:
```json
{
  "case_id": "uuid",
  "officer_id": "OFC-123",
  "action": "SECONDARY_INSPECTION",
  "reason": "Watchlist unavailable - need manual verification",
  "notes": "Referred to supervisor for callback"
}
```

**Response**:
```json
{
  "id": "uuid",
  "case_id": "uuid",
  "officer_id": "OFC-123",
  "action": "SECONDARY_INSPECTION",
  "timestamp": "2026-01-15T10:40:00Z"
}
```

### GET `/officer-actions/{case_id}`
Get officer action history for a case.

---

## Sync & Status

### GET `/sync/queue`
Get sync queue status.

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "operation_type": "STATUS_CHECK",
      "entity_identifier": "P<IND12345678",
      "status_type": "WATCHLIST",
      "priority": "HIGH",
      "status": "PENDING",
      "retry_count": 0,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "stats": {"pending": 5, "processing": 1, "completed": 42, "failed": 2}
}
```

### POST `/sync/trigger`
Manually trigger sync for a case or entity.

**Request**:
```json
{
  "case_id": "uuid",
  "operation_type": "STATUS_CHECK",
  "entity_identifier": "P<IND12345678",
  "status_type": "WATCHLIST",
  "priority": "CRITICAL"
}
```

### GET `/status-cache/{case_id}`
Get cached status checks for a case.

---

## Audit Trail

### GET `/audit/{case_id}`
Get audit log for a case (with hash chain verification).

**Response**:
```json
{
  "records": [
    {
      "id": "uuid",
      "action": "DOCUMENT_UPLOADED",
      "actor_id": "OFC-123",
      "actor_type": "OFFICER",
      "result": "SUCCESS",
      "timestamp": "2026-01-15T10:30:00Z",
      "hash": "sha256...",
      "previous_hash": "sha256...",
      "details": {"document_type": "PASSPORT"}
    }
  ],
  "chain_verified": true,
  "total_records": 25
}
```

### GET `/audit/{case_id}/verify`
Verify hash chain integrity.

**Response**:
```json
{
  "intact": true,
  "broken_links": 0,
  "total_records": 25,
  "verified_at": "2026-01-15T10:45:00Z"
}
```

---

## Demo Scenarios

### GET `/demo/scenarios`
List all 7 mandated demo scenarios.

**Response**:
```json
{
  "scenarios": [
    {"id": "scenario_1", "name": "Clean Traveler", "description": "Valid passport, valid visa, face match, clean watchlist"},
    {"id": "scenario_2", "name": "Expired Passport", "description": "Passport expired, valid visa"},
    {"id": "scenario_3", "name": "Face Mismatch", "description": "Valid documents but live face doesn't match"},
    {"id": "scenario_4", "name": "Watchlist Hit", "description": "Passport on INTERPOL SLTD"},
    {"id": "scenario_5", "name": "Document Tampering", "description": "Photo substitution and data alteration"},
    {"id": "scenario_6", "name": "Identity Fragmentation", "description": "Conflicting data between documents"},
    {"id": "scenario_7", "name": "Offline Mode", "description": "Central databases unreachable"}
  ]
}
```

### POST `/demo/scenarios/{scenario_id}/run`
Execute a demo scenario end-to-end.

**Response**:
```json
{
  "case_id": "uuid",
  "case_number": "DEMO-S1-001",
  "scenario": "scenario_1",
  "message": "Scenario executed successfully"
}
```

### POST `/demo/load-test-data`
Load all synthetic test data into database.

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Human-readable error message",
  "error_code": "VALIDATION_ERROR | NOT_FOUND | PROCESSING_ERROR | SYNC_ERROR",
  "details": {}
}
```

**HTTP Status Codes**:
- 200: Success
- 201: Created
- 202: Accepted (async processing)
- 400: Bad Request (validation)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 409: Conflict
- 422: Unprocessable Entity
- 500: Internal Server Error
- 503: Service Unavailable (models loading, DB down)

---

## WebSocket (Future)

Real-time updates for:
- Case status changes
- Sync queue progress
- Fusion result updates

`ws://localhost:8000/ws/{case_id}`

---

## Rate Limiting

- 100 requests/minute per IP (configurable)
- Burst: 20 requests/second
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Versioning

API version in URL: `/api/v1/...`  
Current: v1 (implicit)