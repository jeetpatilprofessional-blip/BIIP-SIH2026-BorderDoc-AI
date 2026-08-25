# BIIP-SIH2026 Security & Privacy Documentation

## Security Overview

This document describes the security architecture, privacy considerations, and compliance posture of the BIIP-SIH2026 system.

**⚠️ CRITICAL**: This is a **hackathon prototype**. The security controls described here are **design targets** - most are **NOT IMPLEMENTED** in the current codebase. See [Limitations](limitations.md) for details.

---

## Threat Model

### Assets to Protect
| Asset | Classification | Impact if Compromised |
|-------|----------------|----------------------|
| Biometric templates (face embeddings) | HIGHLY SENSITIVE | Identity theft, tracking |
| Travel documents (passport/visa data) | HIGHLY SENSITIVE | Identity fraud, border breaches |
| Watchlist/Adverse records | CLASSIFIED | Operational security |
| Officer identities & decisions | SENSITIVE | Corruption risk, retaliation |
| Audit trail integrity | CRITICAL | Repudiation, evidence tampering |
| System configuration | SENSITIVE | Attack surface expansion |

### Threat Actors
| Actor | Motivation | Capability |
|-------|------------|------------|
| External attacker | Data theft, system disruption | Network access, exploit kits |
| Malicious insider | Data exfiltration, sabotage | Legitimate access, credentials |
| Corrupt officer | Favorable decisions, evidence tampering | System access, authority |
| Nation-state | Intelligence, watchlist manipulation | Advanced persistent threats |
| Accidental exposure | Misconfiguration, lost device | Low |

### Attack Vectors
1. **Network**: MITM, API abuse, DoS
2. **Application**: Injection, auth bypass, file upload
3. **Data**: SQL injection, insecure storage, backup theft
4. **ML Models**: Adversarial inputs, model extraction
5. **Supply Chain**: Compromised dependencies
6. **Physical**: Device theft, shoulder surfing

---

## Security Controls (Design Targets)

### 1. Network Security
```
┌─────────────────────────────────────────────────────────────┐
│                    NETWORK ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INTERNET                                                    │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────┐    mTLS    ┌──────────┐    mTLS    ┌────────┐ │
│  │  WAF    │───────────▶│  API GW  │───────────▶│ BACKEND│ │
│  │ (Rate   │            │ (AuthZ)  │            │ (API)  │ │
│  │  Limit) │            │          │            │        │ │
│  └─────────┘            └──────────┘            └────┬───┘ │
│                                                        │     │
│                    ┌─────────────────────────────────┘     │
│                    ▼                                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              PRIVATE NETWORK (VPC)                   │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │  │
│  │  │PostgreSQL│  │ Redis   │  │ Models  │  │ Central│  │  │
│  │  │  (Enc)  │  │ (Cache) │  │ (GPU)   │  │  Sys   │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Required Controls**:
- [ ] TLS 1.3 everywhere (external + internal)
- [ ] mTLS for service-to-service (SPIFFE/SPIRE)
- [ ] WAF with OWASP Core Rule Set
- [ ] API Gateway with rate limiting, auth
- [ ] Private subnets, no direct DB access
- [ ] VPC flow logs

### 2. Authentication & Authorization

#### Authentication (Design)
```yaml
# Target Architecture
auth:
  method: OIDC/OAuth2
  providers:
    - Azure AD (government)
    - Custom IdP (PKI-based)
  mfa:
    required: true
    methods: [FIDO2, TOTP, PIV/CAC]
  session:
    timeout: 15min
    absolute_timeout: 8hr
```

#### Authorization (RBAC Design)
| Role | Permissions |
|------|-------------|
| `OFFICER` | Create cases, upload docs, capture face, view recommendations, record decisions |
| `SUPERVISOR` | All OFFICER + override decisions, view all cases, manage officer assignments |
| `ADMIN` | All SUPERVISOR + system config, rule management, user management, audit export |
| `AUDITOR` | Read-only access to cases, evidence, audit trails |
| `SYSTEM` | Service-to-service (sync, model inference) |

#### Current Implementation (Prototype)
```python
# backend/app/core/security.py - NOT IMPLEMENTED
# Currently: NO AUTHENTICATION, NO AUTHORIZATION
# All endpoints publicly accessible
```

### 3. Data Protection

#### Encryption at Rest
| Data Type | Algorithm | Key Management |
|-----------|-----------|----------------|
| Database (PostgreSQL) | AES-256 (TDE) | HSM / Cloud KMS |
| File Storage (images) | AES-256-GCM | Per-file DEK, KEK in HSM |
| Backups | AES-256 | Separate backup keys |
| Model weights | AES-256 | Model server keys |

#### Encryption in Transit
| Channel | Protocol | Certificate |
|---------|----------|-------------|
| Client → API | TLS 1.3 | Public CA |
| API → DB | TLS 1.3 | mTLS (SPIFFE) |
| API → Central | TLS 1.3 | mTLS (mutual) |
| API → Model Server | TLS 1.3 | mTLS |
| Sync Queue | TLS 1.3 | mTLS |

#### Field-Level Encryption (PII)
```sql
-- Target: Encrypted columns for PII
CREATE TABLE person (
    id UUID PRIMARY KEY,
    surname_enc BYTEA,      -- AES-256-GCM encrypted
    given_names_enc BYTEA,
    birth_date_enc BYTEA,
    nationality_enc BYTEA,
    -- Searchable hashes for indexing
    surname_hash CHAR(64),  -- HMAC-SHA256(key, lower(surname))
    dob_hash CHAR(64)       -- HMAC-SHA256(key, birth_date::text)
);
```

#### Current Implementation (Prototype)
- ❌ No encryption at rest (plaintext PostgreSQL/SQLite)
- ❌ No encryption in transit (HTTP in dev)
- ❌ No field-level encryption
- ❌ PII stored in plaintext

### 4. Audit Trail Security

#### Hash Chain Design
```
Record 1: hash_1 = SHA256(data_1 || null)
Record 2: hash_2 = SHA256(data_2 || hash_1)
Record 3: hash_3 = SHA256(data_3 || hash_2)
...
Record N: hash_N = SHA256(data_N || hash_{N-1})
```

#### Tamper-Evidence Properties
- **Append-only**: Records never modified/deleted
- **Chained**: Each record commits to predecessor
- **Verifiable**: Anyone can verify chain integrity
- **Non-repudiable**: Officer actions cryptographically bound

#### Production Hardening (Required)
- [ ] HMAC-SHA256 with rotating keys (not plain SHA256)
- [ ] Keys in HSM, never in memory
- [ ] Periodic anchoring to public ledger (e.g., Bitcoin OP_RETURN)
- [ ] Write-once storage (WORM) for audit logs
- [ ] Independent audit log service (separate trust domain)

#### Current Implementation (Prototype)
```python
# backend/app/services/audit/logger.py
# Uses plain SHA256, no HMAC, no key rotation
# Stored in same DB as application data
# Vulnerable to DB admin rewrite
```

### 5. Biometric Data Protection

#### Face Embeddings
- **Storage**: Encrypted BLOB (AES-256-GCM)
- **Retention**: Maximum 90 days (configurable)
- **Access**: Only face verification service
- **Deletion**: Automatic purge after case closure + retention period
- **No raw images**: Only embeddings stored (privacy by design)

#### Liveness Data
- **Challenge responses**: Not stored (ephemeral)
- **Video frames**: Not stored
- **Only result**: `LIVE/SPOOF/UNCERTAIN` + confidence

#### Template Protection
- [ ] Homomorphic encryption for matching (future)
- [ ] Cancelable biometrics (revocable templates)
- [ ] No central biometric database (distributed)

### 6. API Security

#### Input Validation
```python
# All endpoints: Pydantic v2 validation
# File uploads:
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME = ["image/jpeg", "image/png", "application/pdf"]
# Virus scanning: ClamAV integration (required)
```

#### Rate Limiting
```yaml
# Target configuration
rate_limits:
  default: "100/minute"
  auth: "10/minute"
  upload: "5/minute"
  sync: "20/minute"
  burst: "20/second"
```

#### Security Headers
```python
# Target headers
Content-Security-Policy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

### 7. Secrets Management

#### Current (Prototype)
```bash
# .env files - COMMITTED TO GIT (BAD!)
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=hardcoded-secret
CENTRAL_API_KEY=demo-key
```

#### Required (Production)
```yaml
# HashiCorp Vault / AWS Secrets Manager / Azure Key Vault
secrets:
  database:
    path: secret/biip/database
    rotation: 30d
  jwt:
    path: secret/biip/jwt
    rotation: 90d
  central_api:
    path: secret/biip/central
    rotation: 30d
  model_server:
    path: secret/biip/models
  encryption_keys:
    path: secret/biip/encryption
    type: HSM-backed
```

---

## Privacy Considerations

### Data Minimization
| Principle | Implementation |
|-----------|----------------|
| Collect only necessary | Only document fields needed for verification |
| Process locally | Face matching, OCR, tamper detection on-device |
| No central biometric DB | Embeddings never leave border post |
| Purpose limitation | Data used only for border decision |

### Data Retention
| Data Category | Retention Period | Legal Basis |
|---------------|------------------|-------------|
| Case records | 7 years | Border control law |
| Evidence atoms | 7 years | Evidence preservation |
| Audit logs | 7 years + legal hold | Accountability |
| Face embeddings | 90 days post-case | Biometric privacy law |
| Document images | 30 days | Verification review |
| Sync queue | 24 hours post-completion | Operational |
| Officer actions | 7 years | Accountability |

### Data Subject Rights (GDPR/India DPDP)
| Right | Implementation |
|-------|----------------|
| Access | Officer portal: "My Data" export |
| Rectification | Supervisor correction workflow |
| Erasure | Auto-purge per retention; manual for legal hold |
| Portability | JSON export of case data |
| Objection | Opt-out from non-essential processing |
| Automated Decisions | Human-in-the-loop (officer review mandatory) |

### Privacy by Design
1. **Local-first**: All biometric processing on-premise
2. **No surveillance**: No continuous monitoring, only transactional
3. **Pseudonymization**: Case IDs not linked to real identity in analytics
4. **Transparency**: Open source algorithms (where possible)

---

## Compliance Mapping

| Regulation | Applicable | Status |
|------------|------------|--------|
| India DPDP Act 2023 | YES | Design phase |
| GDPR (EU travelers) | YES | Design phase |
| ICAO 9303 (MRZ) | YES | Partial (TD3 only) |
| ISO/IEC 19794-5 (Face) | YES | Partial (InsightFace) |
| ISO/IEC 30107 (Liveness) | YES | Not certified |
| NIST SP 800-53 | Target | Gap analysis needed |
| ISO 27001 | Target | Not started |

---

## Incident Response

### Security Incident Classification
| Severity | Examples | Response Time |
|----------|----------|---------------|
| SEV-1 (Critical) | Data breach, watchlist tampering, biometric theft | 1 hour |
| SEV-2 (High) | Auth bypass, privilege escalation, DoS | 4 hours |
| SEV-3 (Medium) | Info disclosure, config drift | 24 hours |
| SEV-4 (Low) | Minor vuln, log anomaly | 7 days |

### Response Procedures
1. **Detect**: SIEM alerts, audit chain break, anomaly detection
2. **Contain**: Isolate affected system, revoke credentials
3. **Eradicate**: Patch vuln, remove malware, rotate keys
4. **Recover**: Restore from clean backup, verify integrity
5. **Post-Incident**: Root cause, update controls, notify authorities

### Breach Notification
- **DPDP Act**: 72 hours to Data Protection Board
- **Affected individuals**: Without undue delay
- **Regulators**: As required by sectoral laws

---

## Secure Development

### SDLC Integration
| Phase | Security Activity |
|-------|-------------------|
| Design | Threat modeling (STRIDE), privacy impact assessment |
| Code | SAST (Semgrep, Bandit), secrets scanning (TruffleHog) |
| Test | DAST (OWASP ZAP), dependency scan (Dependabot, Snyk) |
| Build | SBOM generation (Syft), image signing (Cosign) |
| Deploy | Policy enforcement (OPA/Gatekeeper), drift detection |
| Operate | Runtime security (Falco), vulnerability management |

### Dependency Management
```bash
# Backend
pip-audit                    # Check for vulnerabilities
pip-tools compile            # Pin dependencies
# requirements.txt with hashes

# Frontend
npm audit                    # Check vulnerabilities
npm audit fix                # Auto-fix
# package-lock.json committed
```

### Code Review Checklist
- [ ] No hardcoded secrets
- [ ] Input validation on all user data
- [ ] Parameterized queries (no string interpolation)
- [ ] Proper error handling (no stack traces to user)
- [ ] Audit logging for sensitive operations
- [ ] Authorization checks on all endpoints
- [ ] No PII in logs
- [ ] Cryptography: use libraries, not custom

---

## Penetration Testing

### Scope (Pre-Production)
- [ ] API endpoints (auth, input validation, rate limiting)
- [ ] File upload (path traversal, malware, DoS)
- [ ] Authentication/Authorization bypass
- [ ] Business logic (decision manipulation)
- [ ] ML model (adversarial face images)
- [ ] Database (injection, privilege escalation)
- [ ] Network (segmentation, encryption)

### Bug Bounty (Future)
- Platform: HackerOne / Intigriti
- Scope: Production API, frontend
- Rewards: Based on severity

---

## Security Checklist for SIH2026 Demo

### Minimum Viable Security for Demo
- [ ] HTTPS for frontend (self-signed cert OK for demo)
- [ ] No secrets in repo (use .env.example)
- [ ] Input validation on file uploads
- [ ] Basic rate limiting (demo-appropriate)
- [ ] Audit hash chain verification demo works
- [ ] No PII in console logs
- [ ] CORS configured properly

### What to Highlight to Judges
1. **"Designed for zero-trust architecture"** - show network diagram
2. **"Audit trail is tamper-evident"** - demonstrate hash chain verification
3. **"Biometrics never leave the border post"** - local processing
4. **"UNAVAILABLE ≠ CLEAR"** - privacy-preserving offline mode
5. **"Explainable decisions"** - no black-box ML for recommendations

---

## Security Contacts

| Role | Contact |
|------|---------|
| Security Lead | [Team Member] |
| Privacy Officer | [Team Member] |
| Incident Commander | [Team Member] |
| External Reporting | cert-in@gov.in (India) |

---

## Related Documentation

- [Architecture](architecture.md) - System design
- [Limitations](limitations.md) - Honest assessment of gaps
- [Database](database.md) - Schema with security notes
- [Teammate Setup](teammate_setup.md) - Secure dev environment