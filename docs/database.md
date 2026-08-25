# BIIP-SIH2026 Database Schema Documentation

## Overview

**Database**: PostgreSQL 15+ (production) / SQLite (development/testing)  
**ORM**: SQLModel (SQLAlchemy 2.0 + Pydantic v2)  
**Migrations**: Alembic (configured in `backend/alembic/`)

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    BIIP DATABASE SCHEMA                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────┐       ┌──────────┐       ┌──────────────────┐       ┌──────────┐     │
│  │   CASE   │       │ PERSON   │       │    DOCUMENT      │       │ DOCUMENT │     │
│  ├──────────┤       ├──────────┤       ├──────────────────┤       │  FIELD   │     │
│  │ id (PK)  │◀──────│ id (PK)  │       │ id (PK)          │◀──────│ id (PK)  │     │
│  │case_num  │       │case_id   │       │case_id (FK)      │       │doc_id(FK)│     │
│  │location  │       │surname   │       │person_id (FK)    │       │field_name│     │
│  │officer_id│       │given_nms │       │doc_type (ENUM)   │       │value     │     │
│  │status    │       │dob       │       │country_code      │       │confidence│     │
│  │created_at│       │nationality│      │doc_number        │       │source    │     │
│  └──────────┘       │confidence│       │mrz_raw           │       └──────────┘     │
│         │           └──────────┘       │mrz_valid         │              │          │
│         │                  │           │barcode_raw       │              │          │
│         │                  │           │proc_status (ENUM)│              │          │
│         │                  │           └────────┬─────────┘              │          │
│         │                  │                    │                       │          │
│         │           ┌──────┴──────┐            │                       │          │
│         │           │             │            │                       │          │
│         ▼           ▼             ▼            ▼                       ▼          │
│  ┌──────────┐  ┌──────────┐ ┌───────────┐ ┌───────────┐         ┌──────────┐     │
│  │ AUDITLOG │  │FACERESULT│ │TAMPERRES  │ │  EVIDENCE │         │SYNCQUEUE │     │
│  ├──────────┤  ├──────────┤ ├───────────┤ ├──────────┤         ├──────────┤     │
│  │id (PK)   │  │id (PK)   │ │id (PK)    │ │id (PK)   │         │id (PK)   │     │
│  │case_id   │  │case_id   │ │doc_id(FK) │ │case_id   │         │case_id   │     │
│  │action    │  │doc_id    │ │tamper_det │ │evi_type  │         │op_type   │     │
│  │actor_id  │  │src_type  │ │anomaly_sc │ │severity  │         │entity_id │     │
│  │actor_type│  │match_sc  │ │regions    │ │source    │         │status    │     │
│  │result    │  │match_res │ │ela_image  │ │confidence│         │priority  │     │
│  │timestamp │  │liveness  │ │sift_img   │ │freshness │         │retry_cnt │     │
│  │hash      │  │liveness_c│ └───────────┘ │descript. │         │max_retries│    │
│  │prev_hash │  │comp_doc  │               │details   │         └──────────┘     │
│  │details   │  └──────────┘               └──────────┘                          │
│  └──────────┘                                     │                             │
│                                                   │                             │
│  ┌──────────┐       ┌──────────────┐       ┌──────┴──────┐                      │
│  │IDENTITY  │       │ STATUS CACHE │       │   RULE      │                      │
│  │  NODE    │       ├──────────────┤       ├─────────────┤                      │
│  ├──────────┤       │ id (PK)      │       │ id (PK)     │                      │
│  │id (PK)   │       │case_id       │       │rule_set_id  │                      │
│  │case_id   │       │entity_id     │       │name         │                      │
│  │node_type │       │status_type   │       │version      │                      │
│  │label     │       │status        │       │rules (JSON) │                      │
│  │attributes│       │freshness     │       │is_active    │                      │
│  │confidence│       │source        │       │created_at   │                      │
│  └──────────┘       │checked_at    │       └─────────────┘                      │
│         │           │expires_at    │                                             │
│         │           └──────────────┘                                             │
│         │                                              ┌──────────────┐            │
│         │                                              │OFFICER ACTION│            │
│         ▼                                              ├──────────────┤            │
│  ┌──────────────┐                                     │ id (PK)      │            │
│  │ IDENTITY     │                                     │ case_id      │            │
│  │  EDGE        │                                     │ officer_id   │            │
│  ├──────────────┤                                     │ action       │            │
│  │id (PK)       │                                     │ reason       │            │
│  │case_id       │                                     │ notes        │            │
│  │src_node_id   │                                     │timestamp     │            │
│  │tgt_node_id   │                                     └──────────────┘            │
│  │edge_type     │                                                         │
│  │description   │                                                         │
│  │confidence    │                                                         │
│  └──────────────┘                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Table Definitions

### `case` - Screening Cases
```sql
CREATE TABLE "case" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number VARCHAR(50) UNIQUE NOT NULL,
    location VARCHAR(50),
    officer_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, IN_PROGRESS, CLOSED
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);
```
**Indexes**: `case_number` (unique), `officer_id`, `status`, `created_at`

---

### `person` - Identity Clusters
```sql
CREATE TABLE person (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    surname VARCHAR(100),
    given_names VARCHAR(200),
    birth_date DATE,
    nationality VARCHAR(3),
    gender VARCHAR(1),
    confidence FLOAT DEFAULT 0.0,  -- clustering confidence
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `surname`, `birth_date`, `nationality`

---

### `document` - Identity Documents
```sql
CREATE TABLE document (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    person_id UUID REFERENCES person(id) ON DELETE SET NULL,
    document_type VARCHAR(20) NOT NULL,  -- PASSPORT, VISA, NATIONAL_ID
    country_code CHAR(3) NOT NULL,
    document_number VARCHAR(100),
    mrz_raw TEXT,
    mrz_valid BOOLEAN DEFAULT FALSE,
    barcode_raw TEXT,
    barcode_valid BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
    image_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `person_id`, `document_number`, `document_type`, `processing_status`

---

### `document_field` - Extracted Fields
```sql
CREATE TABLE document_field (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    value TEXT,
    confidence FLOAT NOT NULL,  -- 0.0-1.0
    source VARCHAR(20) NOT NULL,  -- OCR, MRZ, BARCODE, NFC
    bbox_x INTEGER,  -- bounding box for review
    bbox_y INTEGER,
    bbox_width INTEGER,
    bbox_height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `document_id`, `field_name`, `source`

---

### `face_result` - Face Verification Results
```sql
CREATE TABLE face_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    document_id UUID REFERENCES document(id) ON DELETE SET NULL,
    source_type VARCHAR(20) NOT NULL,  -- LIVE_CAPTURE, DOCUMENT_PORTRAIT
    image_path VARCHAR(500),
    embedding BYTEA,  -- 512-dim float32 serialized
    match_score FLOAT,  -- cosine similarity 0.0-1.0
    match_result VARCHAR(20),  -- MATCH, NO_MATCH, INCONCLUSIVE
    compared_to_document_id UUID REFERENCES document(id),
    liveness_result VARCHAR(20),  -- LIVE, SPOOF, UNCERTAIN
    liveness_confidence FLOAT,
    challenge_type VARCHAR(20),  -- BLINK, TURN, SMILE, NONE
    challenge_passed BOOLEAN,
    processing_status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `document_id`, `match_result`, `liveness_result`

---

### `tamper_result` - Document Forensics
```sql
CREATE TABLE tamper_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    tamper_detected BOOLEAN DEFAULT FALSE,
    anomaly_score FLOAT DEFAULT 0.0,  -- 0.0-1.0 overall
    ela_image_path VARCHAR(500),  -- Error Level Analysis output
    sift_matches INTEGER,  -- copy-move detection
    block_match_regions JSONB,  -- suspicious regions
    font_anomalies JSONB,  -- font consistency issues
    photo_substitution_score FLOAT,
    details JSONB,  -- full region breakdown
    processing_status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `document_id`, `tamper_detected`, `anomaly_score`

---

### `evidence_atom` - Evidence Atoms
```sql
CREATE TABLE evidence_atom (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL,  -- DOCUMENT_VALID, FACE_MATCH, WATCHLIST_HIT, etc.
    severity VARCHAR(20) NOT NULL,  -- INFO, LOW, MEDIUM, HIGH, CRITICAL
    source VARCHAR(50) NOT NULL,  -- MRZ, OCR, BARCODE, FACE_VERIFICATION, WATCHLIST, RULE_ENGINE
    confidence FLOAT NOT NULL,  -- 0.0-1.0
    description TEXT NOT NULL,
    freshness VARCHAR(20) NOT NULL,  -- VERIFIED_FRESH, VERIFIED_STALE, UNAVAILABLE, CONFIRMED_ADVERSE
    details JSONB,  -- structured details for UI
    generated_by VARCHAR(50),  -- service name
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `evidence_type`, `severity`, `source`, `freshness`, `generated_at`

---

### `identity_node` - Identity Graph Nodes
```sql
CREATE TABLE identity_node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    node_type VARCHAR(20) NOT NULL,  -- PERSON, DOCUMENT, FACE, TRAVEL_EVENT
    label VARCHAR(200) NOT NULL,
    attributes JSONB,  -- flexible key-value store
    confidence FLOAT DEFAULT 0.0,
    source_document_id UUID REFERENCES document(id),
    source_face_id UUID REFERENCES face_result(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `node_type`, `source_document_id`, `source_face_id`

---

### `identity_edge` - Identity Graph Edges
```sql
CREATE TABLE identity_edge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES identity_node(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES identity_node(id) ON DELETE CASCADE,
    edge_type VARCHAR(30) NOT NULL,  -- BELONGS_TO, REFERENCES, MATCHES, CONFLICTS_WITH, VALIDATES, OCCURRED_BEFORE
    description TEXT,
    confidence FLOAT DEFAULT 0.0,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `source_node_id`, `target_node_id`, `edge_type`

---

### `audit_log` - Immutable Audit Trail
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,  -- CASE_CREATED, DOCUMENT_UPLOADED, FACE_VERIFIED, etc.
    actor_id VARCHAR(100) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,  -- OFFICER, SYSTEM, SUPERVISOR, ADMIN
    result VARCHAR(20) NOT NULL,  -- SUCCESS, FAILURE, PARTIAL
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    hash CHAR(64) NOT NULL,  -- SHA-256 of this record
    previous_hash CHAR(64),  -- SHA-256 of previous record (hash chain)
    details JSONB,
    
    -- Ensure ordering for hash chain
    CONSTRAINT audit_log_chain_order CHECK (id IS NOT NULL)
);
```
**Indexes**: `case_id`, `action`, `actor_id`, `timestamp`, `hash` (unique)

**Hash Chain Formula**:
```
hash_n = SHA256(
    case_id || action || actor_id || actor_type || result || 
    timestamp || previous_hash || JSON(details)
)
```

---

### `status_cache` - Central Status Caching
```sql
CREATE TABLE status_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES "case"(id) ON DELETE CASCADE,
    entity_identifier VARCHAR(200) NOT NULL,  -- passport number, visa number
    status_type VARCHAR(30) NOT NULL,  -- WATCHLIST, VISA, PASSPORT, BIOMETRIC
    status VARCHAR(30) NOT NULL,  -- CLEAN, WATCHLISTED, VALID, EXPIRED, REVOKED
    freshness VARCHAR(20) NOT NULL,  -- VERIFIED_FRESH, VERIFIED_STALE, UNAVAILABLE, CONFIRMED_ADVERSE
    source VARCHAR(50) NOT NULL,  -- NATIONAL_DB, INTERPOL, VISA_SYSTEM, PASSPORT_REGISTRY
    details JSONB,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- TTL for staleness
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `entity_identifier`, `status_type`, `freshness`, `expires_at`

**Composite Unique**: `(entity_identifier, status_type, case_id)`

---

### `sync_queue` - Offline Sync Queue
```sql
CREATE TABLE sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES "case"(id) ON DELETE CASCADE,
    operation_type VARCHAR(30) NOT NULL,  -- STATUS_CHECK, BIOMETRIC_DEDUP, WATCHLIST_SYNC
    entity_identifier VARCHAR(200) NOT NULL,
    status_type VARCHAR(30),  -- WATCHLIST, VISA, PASSPORT
    priority VARCHAR(20) DEFAULT 'NORMAL',  -- LOW, NORMAL, HIGH, CRITICAL
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
    payload JSONB,  -- request payload
    response JSONB,  -- response from central
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `status`, `priority`, `scheduled_at`, `entity_identifier`

---

### `rule_set` - Business Rules Configuration
```sql
CREATE TABLE rule_set (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    rules JSONB NOT NULL,  -- rule definitions
    is_active BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE
);
```
**Indexes**: `is_active`, `name`

---

### `officer_action` - Officer Decisions
```sql
CREATE TABLE officer_action (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    officer_id VARCHAR(100) NOT NULL,
    action VARCHAR(30) NOT NULL,  -- ALLOW, SECONDARY_INSPECTION, DENY, DETAIN, ESCALATE
    reason TEXT,
    notes TEXT,
    previous_recommendation VARCHAR(30),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```
**Indexes**: `case_id`, `officer_id`, `action`, `timestamp`

---

## Enumerations (Application-Level)

### DocumentType
```python
class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
```

### ProcessingStatus
```python
class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

### EvidenceSeverity
```python
class EvidenceSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

### EvidenceSource
```python
class EvidenceSource(str, Enum):
    MRZ = "MRZ"
    OCR = "OCR"
    BARCODE = "BARCODE"
    NFC = "NFC"
    FACE_VERIFICATION = "FACE_VERIFICATION"
    LIVENESS = "LIVENESS"
    TAMPER_DETECTION = "TAMPER_DETECTION"
    WATCHLIST = "WATCHLIST"
    VISA_SYSTEM = "VISA_SYSTEM"
    PASSPORT_REGISTRY = "PASSPORT_REGISTRY"
    RULE_ENGINE = "RULE_ENGINE"
    IDENTITY_GRAPH = "IDENTITY_GRAPH"
```

### FreshnessState
```python
class FreshnessState(str, Enum):
    VERIFIED_FRESH = "VERIFIED_FRESH"
    VERIFIED_STALE = "VERIFIED_STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"
```

### SyncOperationType
```python
class SyncOperationType(str, Enum):
    STATUS_CHECK = "STATUS_CHECK"
    BIOMETRIC_DEDUP = "BIOMETRIC_DEDUP"
    WATCHLIST_SYNC = "WATCHLIST_SYNC"
    VISA_SYNC = "VISA_SYNC"
    PASSPORT_SYNC = "PASSPORT_SYNC"
```

### SyncStatus
```python
class SyncStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

### SyncPriority
```python
class SyncPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

### NodeType
```python
class NodeType(str, Enum):
    PERSON = "PERSON"
    DOCUMENT = "DOCUMENT"
    FACE = "FACE"
    TRAVEL_EVENT = "TRAVEL_EVENT"
```

### EdgeType
```python
class EdgeType(str, Enum):
    BELONGS_TO = "BELONGS_TO"
    REFERENCES = "REFERENCES"
    MATCHES = "MATCHES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    VALIDATES = "VALIDATES"
    OCCURRED_BEFORE = "OCCURRED_BEFORE"
```

### OfficerActionType
```python
class OfficerActionType(str, Enum):
    ALLOW = "ALLOW"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    DENY = "DENY"
    DETAIN = "DETAIN"
    ESCALATE = "ESCALATE"
```

---

## Freshness TTL Configuration

| Status Type | Fresh TTL | Stale TTL |
|-------------|-----------|-----------|
| WATCHLIST | 4 hours | 24 hours |
| VISA | 24 hours | 72 hours |
| PASSPORT | 24 hours | 72 hours |
| BIOMETRIC | 12 hours | 48 hours |

---

## Migration Strategy

### Initial Migration (v1)
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Adding Columns
```bash
alembic revision --autogenerate -m "add field to document"
alembic upgrade head
```

### Data Migrations
For enum changes or data transformations, create manual migration:
```bash
alembic revision -m "migrate freshness states"
# Edit the generated file with data migration logic
alembic upgrade head
```

---

## Seeding & Test Data

### Demo Scenarios Seed
Run via API: `POST /api/demo/load-test-data`

Or directly:
```python
from app.db.seed import seed_demo_scenarios
seed_demo_scenarios(session)
```

### Rule Sets Seed
```python
from app.db.seed import seed_default_rules
seed_default_rules(session)
```

---

## Performance Considerations

### Partitioning (Future)
- `audit_log`: Partition by month (high volume)
- `evidence_atom`: Partition by case_id (case-scoped queries)
- `sync_queue`: Partition by status (active vs completed)

### Indexing Strategy
- All FK columns indexed
- Composite indexes for common query patterns:
  - `(case_id, evidence_type, freshness)` for evidence queries
  - `(entity_identifier, status_type)` for status cache lookups
  - `(status, priority, scheduled_at)` for sync queue processing

### Query Patterns
| Query | Optimization |
|-------|--------------|
| Case with documents | JOIN with eager loading |
| Evidence for fusion | Filter by case_id + freshness |
| Graph traversal | Recursive CTE or materialized paths |
| Audit verification | Sequential scan by case_id (ordered) |
| Sync processing | Index on (status, priority, scheduled_at) |

---

## Backup & Recovery

- **Point-in-time recovery**: Enabled (WAL archiving)
- **Backup frequency**: Daily full, hourly incremental
- **Retention**: 30 days
- **Audit log**: Immutable, separate backup policy (7 years)

---

## Related Documentation

- [Architecture Overview](architecture.md)
- [API Reference](api.md)
- [Demo Scenarios](demo.md)