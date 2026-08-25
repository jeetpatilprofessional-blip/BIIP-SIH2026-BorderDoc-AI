# BIIP-SIH2026 Architecture Documentation

## System Overview

**Border Identity Intelligence Platform (BIIP)** for **Smart India Hackathon 2026** (SIH2026)

A border control decision-support system that transforms raw document captures into **explainable, evidence-based risk assessments** with full auditability.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BORDER IDENTITY INTELLIGENCE PLATFORM                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ CAPTURE  │───▶│  EXTRACT │───▶│ FORENSICS│───▶│  FACE    │             │
│  │          │    │          │    │          │    │          │             │
│  │ Documents│    │ MRZ/OCR/ │    │ Tamper   │    │ Match +  │             │
│  │ Faces    │    │ Barcode  │    │ Detect   │    │ Liveness │             │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│       │              │              │              │                        │
│       └──────────────┴──────────────┴──────────────┘                        │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    EVIDENCE ATOM GENERATION                          │  │
│  │  Each subsystem emits signed EvidenceAtoms with:                     │  │
│  │  • type • severity (INFO/LOW/MEDIUM/HIGH/CRITICAL)                   │  │
│  │  • source (MRZ/OCR/BARCODE/FACE/WATCHLIST/...)                      │  │
│  │  • confidence (0.0-1.0) • freshness (VERIFIED_FRESH/STALE/UNAVAIL)  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    IDENTITY GRAPH CONSTRUCTION                       │  │
│  │  Nodes: PERSON, PASSPORT, VISA, NATIONAL_ID, FACE, TRAVEL_EVENT     │  │
│  │  Edges: BELONGS_TO, REFERENCES, MATCHES, CONFLICTS_WITH, VALIDATES  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    TRAVEL & RULE ENGINE                              │  │
│  │  • EXPIRY rules (passport/visa expiry)                              │  │
│  │  • FORMAT rules (MRZ checksums, document structure)                 │  │
│  │  • CROSS_FIELD rules (DOB consistency across docs)                  │  │
│  │  • WATCHLIST rules (INTERPOL SLTD, national databases)              │  │
│  │  • VISA_VALIDITY rules (entry/exit dates, type matching)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    EVIDENCE FUSION ENGINE                            │  │
│  │  Additive weighted scoring (NOT black-box ML):                       │  │
│  │  • Positive contributions (valid docs, face match, clean lists)     │  │
│  │  • Negative contributions (expiry, tamper, mismatch, watchlist)     │  │
│  │  • Freshness modifiers (STALE -50%, UNAVAILABLE -80%, ADVERSE +200%)│  │
│  │  • Source reliability weights (MRZ > BARCODE > OCR)                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    EXPLAINABLE RECOMMENDATION                        │  │
│  │  Four tiers with full evidence trail:                                │  │
│  │  • LOW_CONCERN       → Allow entry                                   │  │
│  │  • SECONDARY_INSPECTION → Refer to officer                          │  │
│  │  • HIGH_CONCERN      → Deny / detain                                 │  │
│  │  • INSUFFICIENT_EVIDENCE → Cannot decide (key data missing)         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                          │
│                                  ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    OFFICER REVIEW INTERFACE                          │  │
│  │  • Evidence timeline with severity                                   │  │
│  │  • Identity graph visualization                                      │  │
│  │  • Audit trail (immutable hash chain)                                │  │
│  │  • Officer decision logging                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Design Principles

### 1. Evidence-First Architecture
Every subsystem emits **EvidenceAtoms** — structured, signed pieces of evidence with:
- **Type**: What was checked (DOCUMENT_VALID, FACE_MATCH, WATCHLIST_HIT, etc.)
- **Severity**: INFO, LOW, MEDIUM, HIGH, CRITICAL
- **Source**: Which subsystem/technology produced it (MRZ, OCR, FACE, WATCHLIST, etc.)
- **Confidence**: 0.0-1.0 reliability of this specific finding
- **Freshness**: VERIFIED_FRESH, VERIFIED_STALE, UNAVAILABLE, CONFIRMED_ADVERSE

### 2. Freshness States (CRITICAL Distinction)
| State | Meaning | Fusion Impact |
|-------|---------|---------------|
| `VERIFIED_FRESH` | Recently confirmed from authoritative source | Full weight |
| `VERIFIED_STALE` | Confirmed but older than TTL | 50% weight penalty |
| `UNAVAILABLE` | **Central DB unreachable** — NOT "clean"! | 80% weight penalty |
| `CONFIRMED_ADVERSE` | Authoritative adverse finding (watchlist hit) | 200% negative boost |

**KEY**: `UNAVAILABLE ≠ CLEAR`. This is the #1 judge trap.

### 3. Additive Fusion (Not Black-Box)
```
net_score = positive_contributions - negative_contributions
confidence = weighted_average(confidences, adjusted_by_freshness_and_source)

Recommendation = f(net_score, confidence, critical_flags)
```
Every contribution is traceable. No hidden ML model.

### 4. Offline-First Design
- All local functions (OCR, MRZ, tamper, face) run **without network**
- Central checks (watchlist, visa, passport status) queue locally
- **SyncProcessor** manages priority queue with retry/backoff
- On reconnection: replay queue, reconcile conflicts, update freshness

### 5. Immutable Audit Trail
- Every action logged with **hash chain** (each record includes previous hash)
- Tamper-evident: any modification breaks the chain
- Covers: document upload, face capture, evidence generation, fusion, officer decision

---

## Data Flow Details

### Document Capture → Extraction
1. **Input**: Image upload (passport, visa, national ID, live face)
2. **OCR**: Tesseract + layout analysis for text fields
3. **MRZ**: Parse TD3 format (2 lines × 44 chars), validate checksums
4. **Barcode**: Parse PDF417/QR on visas, national IDs
5. **Output**: Structured `DocumentField` records with confidence scores

### Document Forensics
1. **Input**: Document image + extracted fields
2. **Checks**: ELA (Error Level Analysis), copy-move detection, font consistency, photo substitution
3. **Output**: `TamperResult` with per-region anomaly scores + `EvidenceAtoms`

### Face Verification + Liveness
1. **Input**: Live face capture + document portrait (from MRZ/OCR)
2. **Embedding**: InsightFace (ArcFace) 512-d embeddings
3. **Match**: Cosine similarity with threshold calibration
4. **Liveness**: Texture analysis + motion challenge (blink/turn)
5. **Output**: `FaceResult` with match_score, liveness_result + `EvidenceAtoms`

### Identity Graph
1. **Nodes**: 
   - `PERSON` (clustered from documents + faces)
   - `DOCUMENT` (PASSPORT, VISA, NATIONAL_ID)
   - `FACE` (live capture, document portraits)
   - `TRAVEL_EVENT` (entry/exit from visa/immigration stamps)
2. **Edges**:
   - `BELONGS_TO`: Document → Person
   - `REFERENCES`: Visa → Passport (by passport_number)
   - `MATCHES`: Face → Document (with score)
   - `CONFLICTS_WITH`: Field mismatches (DOB, name, nationality)
   - `VALIDATES`: Visa validates passport (dates, type)
   - `OCCURRED_BEFORE`: Travel event ordering

### Rules Engine
Deterministic rules evaluated against extracted data:
- **EXPIRY**: `expiry_date < now` → CRITICAL
- **FORMAT**: MRZ checksum invalid → HIGH
- **CROSS_FIELD**: DOB mismatch between passport/visa → HIGH
- **WATCHLIST**: Document number in SLTD → CRITICAL (CONFIRMED_ADVERSE)
- **VISA_VALIDITY**: Entry before issue / exit after expiry → HIGH

### Evidence Fusion
```
For each EvidenceAtom:
  base_weight = severity_weight × confidence × source_reliability
  freshness_modifier = 
    VERIFIED_FRESH: 1.0
    VERIFIED_STALE: 0.5
    UNAVAILABLE: 0.2
    CONFIRMED_ADVERSE: 2.0 (for negative) / 0 (for positive)
  
  contribution = base_weight × freshness_modifier
  if atom is positive: positive_sum += contribution
  else: negative_sum += contribution

net = positive_sum - negative_sum
confidence = (positive_conf × positive_sum + negative_conf × negative_sum) / (positive_sum + negative_sum)

Recommendation thresholds:
  net ≥ 0.7 && conf ≥ 0.8 → LOW_CONCERN
  net ≤ -0.5 && conf ≥ 0.7 → HIGH_CONCERN
  net ∈ (-0.5, 0.7) → SECONDARY_INSPECTION
  key_freshness = UNAVAILABLE → INSUFFICIENT_EVIDENCE
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **API** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL (production) / SQLite (dev/test) |
| **ORM** | SQLModel (SQLAlchemy + Pydantic) |
| **OCR** | Tesseract 5.x + custom layout |
| **MRZ** | Custom TD3 parser with checksum validation |
| **Barcode** | OpenCV + pyzbar |
| **Tamper** | OpenCV (ELA, SIFT, block matching) |
| **Face** | InsightFace (ONNX Runtime) - ArcFace |
| **Liveness** | Custom texture + motion analysis |
| **Frontend** | React 18 + TypeScript + Vite |
| **UI** | Tailwind CSS + custom components |
| **Graph Viz** | Cytoscape.js |
| **Testing** | pytest (unit/integration) |
| **Container** | Docker + docker-compose |

---

## Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FRONTEND      │     │    BACKEND      │     │   DATABASE      │
│   (Nginx/React) │────▶│   (FastAPI)     │────▶│  (PostgreSQL)   │
│   Port 80/443   │     │   Port 8000     │     │   Port 5432     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  MODEL STORAGE  │
                       │  (InsightFace    │
                       │   ONNX models)  │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  CENTRAL SYS    │
                       │  (Simulated)    │
                       │  Watchlist/Visa │
                       │  Passport Status│
                       └─────────────────┘
```

### Offline Mode
```
┌─────────────────────────────────────────────────────────────┐
│                    OFFLINE OPERATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Local Processing (always works):                          │
│  ✓ OCR / MRZ / Barcode extraction                          │
│  ✓ Document forensics (tamper detection)                   │
│  ✓ Face match + liveness                                   │
│  ✓ Identity graph construction                             │
│  ✓ Local rules (expiry, format, cross-field)               │
│  ✓ Evidence atom generation                                │
│  ✓ Fusion scoring (local evidence only)                    │
│  ✓ Audit logging                                           │
│                                                             │
│  Queued for Sync (when online):                            │
│  ☐ Central watchlist check                                 │
│  ☐ Central visa status check                               │
│  ☐ Central passport status check                           │
│  ☐ Biometric deduplication (central)                       │
│                                                             │
│  Freshness Impact:                                         │
│  - Central checks → UNAVAILABLE (not CLEAR!)              │
│  - Fusion penalizes UNAVAILABLE heavily                    │
│  - Recommendation may be INSUFFICIENT_EVIDENCE             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Security & Privacy

- **No PII in logs**: Only case IDs, hashes, action types
- **Images**: Stored locally, not transmitted to central (demo)
- **Audit hash chain**: SHA-256 chained hashes
- **Role-based access**: Officer, Supervisor, Admin
- **Data retention**: Configurable TTL per data type

---

## Scalability Considerations

| Component | Scaling Strategy |
|-----------|------------------|
| API | Horizontal (stateless), load balancer |
| Database | Read replicas, connection pooling |
| OCR/Face | GPU workers, queue-based (Celery/Redis) |
| Sync | Priority queue, exponential backoff |
| Models | ONNX Runtime, batch inference |

---

## Integration Points

| External System | Interface | Auth |
|-----------------|-----------|------|
| National Watchlist | REST + mTLS | Certificate |
| Visa Management | REST + mTLS | Certificate |
| Passport Registry | REST + mTLS | Certificate |
| Biometric DB | gRPC | mTLS |
| INTERPOL SLTD | Periodic sync | Certificate |

---

## Monitoring & Observability

- **Health**: `/health` (liveness), `/health/ready` (readiness)
- **Metrics**: Prometheus `/metrics` (request latency, queue depth, error rates)
- **Logs**: Structured JSON, correlated by `case_id`
- **Audit**: Separate immutable log store
- **Traces**: OpenTelemetry (future)

---

## Related Documentation

- [API Reference](api.md)
- [Database Schema](database.md)
- [Demo Scenarios](demo.md)
- [Limitations & Known Issues](limitations.md)
- [Teammate Setup Guide](teammate_setup.md)
- [Security & Privacy](security_privacy.md)