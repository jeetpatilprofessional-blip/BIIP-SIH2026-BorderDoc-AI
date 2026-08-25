# BIIP-SIH2026 Limitations & Known Issues

## Overview

This document transparently documents the known limitations, constraints, and prototype-level implementations in the BIIP-SIH2026 system. This is a **hackathon prototype** - not production-ready software.

---

## Core Architecture Limitations

### 1. Prototype OCR Engine
- **Limitation**: Tesseract-only OCR with basic layout analysis
- **Impact**: Lower accuracy on low-quality images, glare, complex backgrounds
- **Production Need**: Commercial OCR (Google Vision, AWS Textract, ABBYY) with document-specific models
- **Workaround**: Demo uses synthetic clean images

### 2. MRZ Parser Scope
- **Limitation**: TD3 format only (passport MRZ)
- **Impact**: Cannot parse TD1 (ID cards), TD2 (visas), or non-ICAO formats
- **Production Need**: Full ICAO 9303 support for all document types
- **Location**: `backend/app/services/document/validator.py`

### 3. Barcode Parsing
- **Limitation**: Basic pyzbar/OpenCV parsing, limited to PDF417/QR
- **Impact**: May fail on damaged, rotated, or non-standard barcodes
- **Production Need**: Commercial barcode SDK with error correction

### 4. Face Verification (InsightFace)
- **Limitation**: 
  - ONNX Runtime CPU inference (slow: ~200-500ms per embedding)
  - No GPU acceleration configured
  - Threshold calibration is fixed (0.6 cosine similarity)
  - No demographic bias testing
- **Impact**: Latency issues at scale; potential bias
- **Production Need**: 
  - GPU-accelerated inference (TensorRT, ONNX CUDA)
  - Calibrated thresholds per demographic
  - Bias audit and mitigation
  - Liveness: Only texture + simple motion challenge (not iBeta certified)

### 5. Tamper Detection
- **Limitation**: 
  - ELA (Error Level Analysis) sensitive to compression artifacts
  - SIFT copy-move detection fails on uniform regions
  - Font analysis is heuristic-based
  - No PRNU (Photo Response Non-Uniformity) sensor fingerprinting
- **Impact**: False positives on compressed images; misses sophisticated tampering
- **Production Need**: Commercial forensic SDK (e.g., Amped, Forensic Toolkit)

---

## Evidence & Fusion Limitations

### 6. Fixed Fusion Weights
- **Limitation**: Hardcoded severity weights and source reliability
- **Impact**: Cannot adapt to operational feedback without code changes
- **Production Need**: Configurable weight matrix with A/B testing framework

### 7. Freshness TTL Hardcoded
- **Limitation**: TTL values in code, not configuration
- **Impact**: Cannot adjust staleness thresholds per deployment
- **Location**: `backend/app/services/freshness/engine.py`

### 8. No Evidence Versioning
- **Limitation**: Evidence atoms are immutable once created
- **Impact**: Cannot represent "this evidence was superseded by newer check"
- **Production Need**: Evidence versioning with supersession links

### 9. Fusion Confidence Calculation
- **Limitation**: Simple weighted average, not statistically rigorous
- **Impact**: Confidence scores not calibrated probabilities
- **Production Need**: Proper calibration (Platt scaling, isotonic regression)

---

## Identity Graph Limitations

### 10. Simple Clustering
- **Limitation**: Rule-based clustering only (name + DOB + document number)
- **Impact**: Cannot resolve complex identity fragmentation (aliases, transliteration)
- **Production Need**: Probabilistic entity resolution with ML

### 11. No Temporal Graph
- **Limitation**: Graph is static snapshot per case
- **Impact**: Cannot track identity evolution over time
- **Production Need**: Temporal graph with versioned nodes/edges

### 12. Limited Edge Types
- **Limitation**: Only 6 edge types defined
- **Impact**: Cannot represent complex relationships (family, sponsor, employer)
- **Production Need**: Extensible edge ontology

---

## Sync & Offline Limitations

### 13. Simulated Central Services
- **Limitation**: `CentralServiceClient` uses in-memory `SIMULATED_WATCHLIST` dict
- **Impact**: No real integration with national databases, INTERPOL, visa systems
- **Production Need**: 
  - mTLS authentication
  - Circuit breakers
  - Proper API contracts (OpenAPI specs)
  - Rate limiting compliance

### 14. Sync Conflict Resolution
- **Limitation**: Last-write-wins, no sophisticated conflict resolution
- **Impact**: Potential data loss on concurrent updates
- **Production Need**: Operational transformation or CRDTs

### 15. No Queue Persistence Across Restarts
- **Limitation**: In-memory queue processing (though DB-backed)
- **Impact**: Processing state lost on crash (though items remain in DB)
- **Production Need**: Distributed queue (Redis/RabbitMQ) with consumer groups

---

## Database Limitations

### 16. SQLite for Development Only
- **Limitation**: No concurrent write support, no advisory locks
- **Impact**: Not suitable for multi-user testing
- **Production Need**: PostgreSQL with proper connection pooling

### 17. No Partitioning
- **Limitation**: Large tables (audit_log, evidence_atom) not partitioned
- **Impact**: Query performance degrades with volume
- **Production Need**: Time-based partitioning strategy

### 18. JSONB Overuse
- **Limitation**: `details` columns use JSONB extensively
- **Impact**: Hard to query, no schema enforcement, indexing limited
- **Production Need**: Normalized tables for frequently queried fields

---

## API & Frontend Limitations

### 19. No Authentication/Authorization
- **Limitation**: All endpoints open, no RBAC
- **Impact**: Not deployable in real environment
- **Production Need**: OAuth2/OIDC, JWT, role-based access control

### 20. No Rate Limiting
- **Limitation**: No request throttling
- **Impact**: Vulnerable to DoS
- **Production Need**: Token bucket / sliding window rate limiter

### 21. No Input Validation on Uploads
- **Limitation**: File type/size validation minimal
- **Impact**: Potential upload attacks
- **Production Need**: MIME validation, size limits, virus scanning

### 22. Frontend State Management
- **Limitation**: React Context only, no Redux/Zustand
- **Impact**: Prop drilling, re-render issues at scale
- **Production Need**: Proper state management library

### 23. No Real-time Updates
- **Limitation**: Polling only, no WebSockets
- **Impact**: Stale UI during long processing
- **Production Need**: WebSocket or Server-Sent Events

---

## Security Limitations

### 24. No Encryption at Rest
- **Limitation**: Database unencrypted, images stored plaintext
- **Impact**: Data exposure if storage compromised
- **Production Need**: TDE (Transparent Data Encryption), encrypted file storage

### 25. No Encryption in Transit (Dev)
- **Limitation**: HTTP in development, no mTLS
- **Impact**: Credential/PII exposure on network
- **Production Need**: TLS 1.3 everywhere, mTLS for service-to-service

### 26. Audit Hash Chain Not Cryptographically Strong
- **Limitation**: SHA-256 but no HMAC, no key rotation
- **Impact**: If DB compromised, chain can be rewritten
- **Production Need**: HSM-backed signing, key rotation, append-only log (e.g., AWS QLDB)

### 27. PII in Database
- **Limitation**: Names, DOB, document numbers stored in plaintext
- **Impact**: GDPR/privacy law compliance issues
- **Production Need**: Field-level encryption, tokenization, pseudonymization

### 28. No Secrets Management
- **Limitation**: Config in `.env` files
- **Impact**: Secrets in git history risk
- **Production Need**: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault

---

## Testing Limitations

### 29. Limited Test Coverage
- **Limitation**: Unit tests for core services only, no contract tests
- **Impact**: Integration gaps, no performance benchmarks
- **Production Need**: 
  - Contract testing (Pact)
  - Load testing (k6, Locust)
  - Chaos engineering
  - Mutation testing

### 30. No Synthetic Data Generation
- **Limitation**: Demo data is hand-crafted SVGs
- **Impact**: Cannot stress-test with volume
- **Production Need**: Programmatic test data generator with variations

---

## Operational Limitations

### 31. No Observability Stack
- **Limitation**: Basic logging only, no metrics/traces
- **Impact**: Cannot debug production issues
- **Production Need**: OpenTelemetry, Prometheus, Grafana, Jaeger

### 32. No Deployment Automation
- **Limitation**: Manual Docker build/deploy
- **Impact**: Error-prone, no rollback
- **Production Need**: CI/CD (GitHub Actions, ArgoCD), blue-green deploy

### 33. No Configuration Management
- **Limitation**: Hardcoded values throughout codebase
- **Impact**: Environment-specific changes require code edits
- **Production Need**: External config (Consul, etcd, Spring Config)

### 34. Single-Instance Design
- **Limitation**: No horizontal scaling patterns
- **Impact**: Cannot handle load
- **Production Need**: Stateless services, shared-nothing architecture

---

## Compliance & Legal Limitations

### 35. No Data Retention Policy
- **Limitation**: No automated purging
- **Impact**: Unbounded storage growth, legal risk
- **Production Need**: Configurable retention with legal hold

### 36. No Audit Export
- **Limitation**: Cannot export audit trail for legal review
- **Impact**: Cannot satisfy regulatory requests
- **Production Need**: Signed export (PDF/JSON with verification)

### 37. No Privacy Impact Assessment
- **Limitation**: No DPIA conducted
- **Impact**: Unknown compliance gaps
- **Production Need**: Formal DPIA before production

---

## Performance Limitations

### 38. Synchronous Processing
- **Limitation**: Document processing blocks API request
- **Impact**: Timeouts on large files, poor UX
- **Production Need**: Async job queue (Celery + Redis), progress callbacks

### 39. No Caching
- **Limitation**: No Redis/Memcached
- **Impact**: Repeated DB queries for same data
- **Production Need**: Multi-level caching strategy

### 40. Model Loading at Startup
- **Limitation**: InsightFace models load on API startup (~5-10s)
- **Impact**: Slow cold starts, health check failures
- **Production Need**: Pre-warmed model servers, lazy loading

---

## Prioritization for Production

| Priority | Items |
|----------|-------|
| **P0 (Blocker)** | 19, 24, 25, 27, 28, 35 |
| **P1 (Critical)** | 1, 4, 5, 13, 14, 31, 32, 38 |
| **P2 (High)** | 2, 3, 6, 7, 10, 11, 16, 17, 20, 21, 22, 23, 29, 33, 34, 39, 40 |
| **P3 (Medium)** | 8, 9, 12, 15, 18, 26, 30, 36, 37 |

---

## Honest Assessment for Judges

**This is a prototype demonstrating architecture and concepts, not a production system.**

What works well:
- ✅ Clean architecture with clear separation of concerns
- ✅ Evidence-first design with explainable fusion
- ✅ Freshness model (UNAVAILABLE ≠ CLEAR)
- ✅ Identity graph with conflict detection
- ✅ Immutable audit trail with hash chain
- ✅ Offline-first sync queue design
- ✅ 7 comprehensive demo scenarios
- ✅ Test coverage for core logic

What needs work before production:
- ❌ Real OCR/face/tamper accuracy
- ❌ Authentication, authorization, encryption
- ❌ Real central system integration
- ❌ Observability, deployment, scaling
- ❌ Compliance (GDPR, data retention)
- ❌ Performance optimization

---

## Related Documentation

- [Architecture](architecture.md)
- [Security & Privacy](security_privacy.md)
- [Teammate Setup](teammate_setup.md)