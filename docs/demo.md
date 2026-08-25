# BIIP-SIH2026 Demo Scenarios Documentation

## Overview

This document describes the **7 mandated demo scenarios** for the Smart India Hackathon 2026 submission. Each scenario demonstrates a specific capability of the Border Identity Intelligence Platform and produces a distinct, explainable recommendation.

---

## Scenario Catalog

| ID | Name | Description | Expected Recommendation | Key Evidence |
|----|------|-------------|------------------------|--------------|
| 1 | Clean Traveler | Valid passport, valid visa, face match, clean watchlist | `LOW_CONCERN` | All positive, fresh |
| 2 | Expired Passport | Passport expired, valid visa | `HIGH_CONCERN` | CRITICAL expiry |
| 3 | Face Mismatch | Valid documents but live face doesn't match | `HIGH_CONCERN` | HIGH face mismatch |
| 4 | Watchlist Hit | Passport on INTERPOL SLTD | `HIGH_CONCERN` | CRITICAL watchlist (CONFIRMED_ADVERSE) |
| 5 | Document Tampering | Photo substitution and data alteration | `HIGH_CONCERN` | CRITICAL tamper |
| 6 | Identity Fragmentation | Conflicting data between documents | `SECONDARY_INSPECTION` | HIGH cross-field conflicts |
| 7 | Offline Mode | Central databases unreachable | `INSUFFICIENT_EVIDENCE` | Key data UNAVAILABLE |

---

## Scenario 1: Clean Traveler

### Description
A legitimate traveler with all valid documents, matching face, and clean background checks.

### Test Data
- **Passport**: Valid (expires 2030), MRZ valid, no tamper
- **Visa**: Valid tourist visa, matches passport, valid dates
- **Face**: Live capture matches passport photo (0.92+ similarity)
- **Liveness**: LIVE (passes blink challenge)
- **Watchlist**: CLEAN (VERIFIED_FRESH)
- **Central Status**: All VERIFIED_FRESH

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_VALID | LOW | MRZ | VERIFIED_FRESH | Passport MRZ valid, checksums OK |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa barcode valid |
| FACE_MATCH | LOW | FACE_VERIFICATION | VERIFIED_FRESH | Live face matches passport (0.92) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Liveness challenge passed |
| WATCHLIST_CLEAN | INFO | WATCHLIST | VERIFIED_FRESH | Not on INTERPOL SLTD |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid for entry |
| PASSPORT_VALID | LOW | PASSPORT_REGISTRY | VERIFIED_FRESH | Passport valid in registry |
| CROSS_FIELD_CONSISTENT | INFO | RULE_ENGINE | VERIFIED_FRESH | DOB matches across docs |

### Fusion Result
```
Positive Score: 0.85
Negative Score: 0.00
Net Score: 0.85
Confidence: 0.92
Recommendation: LOW_CONCERN
```

### Officer Action
- **Recommended**: ALLOW
- **Requires Supervisor**: No

---

## Scenario 2: Expired Passport

### Description
Traveler presents an expired passport but valid visa.

### Test Data
- **Passport**: EXPIRED (expiry 2020-01-01), MRZ valid
- **Visa**: Valid, matches passport number
- **Face**: Matches (0.89)
- **Liveness**: LIVE
- **Watchlist**: CLEAN
- **Central Status**: VERIFIED_FRESH

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_EXPIRED | CRITICAL | RULE_ENGINE | VERIFIED_FRESH | Passport expired 2020-01-01 |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa barcode valid |
| FACE_MATCH | LOW | FACE_VERIFICATION | VERIFIED_FRESH | Live face matches (0.89) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Liveness challenge passed |
| WATCHLIST_CLEAN | INFO | WATCHLIST | VERIFIED_FRESH | Not on watchlist |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid |
| CROSS_FIELD_CONSISTENT | INFO | RULE_ENGINE | VERIFIED_FRESH | DOB matches |

### Fusion Result
```
Positive Score: 0.35
Negative Score: 1.00  (CRITICAL expiry × 1.0 weight)
Net Score: -0.65
Confidence: 0.95
Recommendation: HIGH_CONCERN
Critical Flags: [DOCUMENT_EXPIRED]
```

### Officer Action
- **Recommended**: DENY / DETAIN
- **Requires Supervisor**: Yes

---

## Scenario 3: Face Mismatch

### Description
Valid documents but live face capture doesn't match passport photo (different person).

### Test Data
- **Passport**: Valid, MRZ valid
- **Visa**: Valid, matches passport
- **Face**: NO_MATCH (similarity 0.35)
- **Liveness**: LIVE (real person, just not the passport holder)
- **Watchlist**: CLEAN
- **Central Status**: VERIFIED_FRESH

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_VALID | LOW | MRZ | VERIFIED_FRESH | Passport MRZ valid |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa valid |
| FACE_MISMATCH | HIGH | FACE_VERIFICATION | VERIFIED_FRESH | Face mismatch (0.35) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Live person detected |
| WATCHLIST_CLEAN | INFO | WATCHLIST | VERIFIED_FRESH | Not on watchlist |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid |
| PASSPORT_VALID | LOW | PASSPORT_REGISTRY | VERIFIED_FRESH | Passport valid |
| CROSS_FIELD_CONSISTENT | INFO | RULE_ENGINE | VERIFIED_FRESH | DOB matches |

### Fusion Result
```
Positive Score: 0.42
Negative Score: 0.75  (HIGH face mismatch × 0.75 weight)
Net Score: -0.33
Confidence: 0.88
Recommendation: HIGH_CONCERN
Critical Flags: [FACE_MISMATCH]
```

### Officer Action
- **Recommended**: DENY / DETAIN
- **Requires Supervisor**: Yes

---

## Scenario 4: Watchlist Hit

### Description
Passport number matches INTERPOL Stolen and Lost Travel Documents (SLTD) database.

### Test Data
- **Passport**: Valid format, MRZ valid
- **Visa**: Valid
- **Face**: Matches (0.91)
- **Liveness**: LIVE
- **Watchlist**: WATCHLISTED (INTERPOL SLTD - "Reported stolen 2023")
- **Central Status**: CONFIRMED_ADVERSE (authoritative adverse)

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_VALID | LOW | MRZ | VERIFIED_FRESH | Passport MRZ valid |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa valid |
| FACE_MATCH | LOW | FACE_VERIFICATION | VERIFIED_FRESH | Face matches (0.91) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Liveness passed |
| WATCHLIST_HIT | CRITICAL | WATCHLIST | CONFIRMED_ADVERSE | On INTERPOL SLTD - stolen |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid |
| PASSPORT_REVOKED | CRITICAL | PASSPORT_REGISTRY | CONFIRMED_ADVERSE | Passport reported stolen |

### Fusion Result
```
Positive Score: 0.35
Negative Score: 2.00  (CRITICAL × 2.0 ADVERSE modifier)
Net Score: -1.65
Confidence: 0.99
Recommendation: HIGH_CONCERN
Critical Flags: [WATCHLIST_HIT, PASSPORT_REVOKED]
```

### Officer Action
- **Recommended**: DETAIN
- **Requires Supervisor**: Yes (immediate)

---

## Scenario 5: Document Tampering

### Description
Physical document shows photo substitution and data alteration detected by forensics.

### Test Data
- **Passport**: Valid MRZ but tamper detected
  - ELA anomaly in photo region (0.87)
  - Copy-move detection in photo area
  - Font inconsistency in surname field
- **Visa**: Valid
- **Face**: Mismatch (0.28) - live face doesn't match substituted photo
- **Liveness**: LIVE
- **Watchlist**: CLEAN
- **Central Status**: VERIFIED_FRESH

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_TAMPER_PHOTO | CRITICAL | TAMPER_DETECTION | VERIFIED_FRESH | Photo substitution detected (ELA: 0.87) |
| DOCUMENT_TAMPER_FONT | HIGH | TAMPER_DETECTION | VERIFIED_FRESH | Font inconsistency in surname |
| DOCUMENT_TAMPER_COPY_MOVE | HIGH | TAMPER_DETECTION | VERIFIED_FRESH | Copy-move in photo region |
| FACE_MISMATCH | HIGH | FACE_VERIFICATION | VERIFIED_FRESH | Face mismatch (0.28) - substituted photo |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Live person |
| WATCHLIST_CLEAN | INFO | WATCHLIST | VERIFIED_FRESH | Not on watchlist |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid |
| MRZ_VALID | LOW | MRZ | VERIFIED_FRESH | MRZ checksums valid |

### Fusion Result
```
Positive Score: 0.25
Negative Score: 1.85  (CRITICAL tamper + HIGH tamper + HIGH mismatch)
Net Score: -1.60
Confidence: 0.94
Recommendation: HIGH_CONCERN
Critical Flags: [DOCUMENT_TAMPER_PHOTO, FACE_MISMATCH]
```

### Officer Action
- **Recommended**: DETAIN
- **Requires Supervisor**: Yes

---

## Scenario 6: Identity Fragmentation

### Description
Conflicting identity data between passport and visa (different DOB, suggesting identity fraud).

### Test Data
- **Passport**: Valid, DOB: 1990-01-15
- **Visa**: Valid format, DOB: 1991-01-15 (CONFLICT!)
- **Face**: Matches passport (0.90)
- **Liveness**: LIVE
- **Watchlist**: CLEAN
- **Central Status**: VERIFIED_FRESH

### Identity Graph Conflicts
```
CONFLICTS_WITH edge: passport.birth_date (1990-01-15) vs visa.birth_date (1991-01-15)
Severity: HIGH
```

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_VALID | LOW | MRZ | VERIFIED_FRESH | Passport MRZ valid |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa barcode valid |
| FACE_MATCH | LOW | FACE_VERIFICATION | VERIFIED_FRESH | Face matches passport (0.90) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Liveness passed |
| WATCHLIST_CLEAN | INFO | WATCHLIST | VERIFIED_FRESH | Not on watchlist |
| VISA_VALID | LOW | VISA_SYSTEM | VERIFIED_FRESH | Visa valid |
| CROSS_FIELD_CONFLICT_DOB | HIGH | RULE_ENGINE | VERIFIED_FRESH | DOB mismatch: 1990 vs 1991 |
| IDENTITY_FRAGMENTATION | HIGH | IDENTITY_GRAPH | VERIFIED_FRESH | Conflicting identity docs |

### Fusion Result
```
Positive Score: 0.45
Negative Score: 0.75  (HIGH conflict + HIGH fragmentation)
Net Score: -0.30
Confidence: 0.78
Recommendation: SECONDARY_INSPECTION
Critical Flags: [CROSS_FIELD_CONFLICT_DOB, IDENTITY_FRAGMENTATION]
```

### Officer Action
- **Recommended**: SECONDARY_INSPECTION
- **Requires Supervisor**: No (but recommended)

---

## Scenario 7: Offline Mode

### Description
Border checkpoint operating without connectivity to central databases (watchlist, visa, passport registry).

### Test Data
- **Passport**: Valid, MRZ valid
- **Visa**: Valid, barcode valid
- **Face**: Matches (0.93)
- **Liveness**: LIVE
- **Watchlist**: UNAVAILABLE (cannot reach central)
- **Visa Status**: UNAVAILABLE
- **Passport Status**: UNAVAILABLE
- **Local Rules**: All pass (expiry, format, cross-field)

### Evidence Atoms Generated
| Type | Severity | Source | Freshness | Description |
|------|----------|--------|-----------|-------------|
| DOCUMENT_VALID | LOW | MRZ | VERIFIED_FRESH | Passport MRZ valid |
| DOCUMENT_VALID | LOW | BARCODE | VERIFIED_FRESH | Visa barcode valid |
| FACE_MATCH | LOW | FACE_VERIFICATION | VERIFIED_FRESH | Face matches (0.93) |
| LIVENESS_PASS | INFO | LIVENESS | VERIFIED_FRESH | Liveness passed |
| WATCHLIST_CLEAN | INFO | WATCHLIST | UNAVAILABLE | Central unreachable - cannot verify |
| VISA_VALID | LOW | VISA_SYSTEM | UNAVAILABLE | Central visa check unavailable |
| PASSPORT_VALID | LOW | PASSPORT_REGISTRY | UNAVAILABLE | Central passport check unavailable |
| CROSS_FIELD_CONSISTENT | INFO | RULE_ENGINE | VERIFIED_FRESH | DOB matches locally |

### Sync Queue Entries Created
| Operation | Entity | Priority | Status |
|-----------|--------|----------|--------|
| STATUS_CHECK | P<IND12345678 | WATCHLIST | CRITICAL | PENDING |
| STATUS_CHECK | VISA_IND_2024_ABC | VISA | HIGH | PENDING |
| STATUS_CHECK | P<IND12345678 | PASSPORT | HIGH | PENDING |

### Fusion Result
```
Positive Score: 0.38 (local only)
Negative Score: 0.00
BUT: 3 UNAVAILABLE atoms (watchlist, visa, passport)
Confidence: 0.45  (heavily penalized by UNAVAILABLE)
Net Score: 0.38
Recommendation: INSUFFICIENT_EVIDENCE
Reason: Key central checks UNAVAILABLE - cannot confirm clean status
```

### Officer Action
- **Recommended**: SECONDARY_INSPECTION (manual verification required)
- **Requires Supervisor**: No
- **Note**: System explicitly warns: "UNAVAILABLE ≠ CLEAR - central verification pending"

---

## Running Demo Scenarios

### Via API
```bash
# List scenarios
curl http://localhost:8000/api/demo/scenarios

# Run specific scenario
curl -X POST http://localhost:8000/api/demo/scenarios/scenario_1/run

# Load all test data
curl -X POST http://localhost:8000/api/demo/load-test-data
```

### Via Frontend
1. Navigate to **Demo Lab** page
2. Select scenario from dropdown
3. Click **Run Scenario**
4. View results in **Screening**, **Evidence**, **Identity Graph**, **Audit** tabs

### Expected Outputs Per Scenario

| Scenario | Case Number Pattern | Recommendation | Key Indicator |
|----------|---------------------|----------------|---------------|
| 1 | DEMO-S1-XXX | LOW_CONCERN | All VERIFIED_FRESH, net > 0.7 |
| 2 | DEMO-S2-XXX | HIGH_CONCERN | CRITICAL expiry |
| 3 | DEMO-S3-XXX | HIGH_CONCERN | HIGH face mismatch |
| 4 | DEMO-S4-XXX | HIGH_CONCERN | CONFIRMED_ADVERSE watchlist |
| 5 | DEMO-S5-XXX | HIGH_CONCERN | CRITICAL tamper |
| 6 | DEMO-S6-XXX | SECONDARY_INSPECTION | HIGH conflicts |
| 7 | DEMO-S7-XXX | INSUFFICIENT_EVIDENCE | UNAVAILABLE central checks |

---

## Synthetic Test Data

All test data is **synthetic** and stored in `demo_data/`:

```
demo_data/
├── faces/
│   ├── scenario_1_live.svg      # Clean match
│   ├── scenario_2_live.svg      # Match (expired passport)
│   ├── scenario_3_live.svg      # Mismatch face
│   ├── scenario_4_live.svg      # Match (watchlisted)
│   ├── scenario_5_live.svg      # Mismatch (tampered photo)
│   ├── scenario_6_live.svg      # Match (conflicting docs)
│   └── scenario_7_live.svg      # Match (offline)
├── documents/
│   ├── passports/
│   │   ├── scenario_1_passport.svg  # Valid
│   │   ├── scenario_2_passport.svg  # Expired
│   │   ├── scenario_3_passport.svg  # Valid
│   │   ├── scenario_4_passport.svg  # Valid (watchlisted number)
│   │   ├── scenario_5_passport.svg  # Tampered
│   │   ├── scenario_6_passport.svg  # Valid (DOB: 1990)
│   │   └── scenario_7_passport.svg  # Valid
│   └── visas/
│       ├── scenario_1_visa.svg
│       ├── scenario_2_visa.svg
│       ├── scenario_3_visa.svg
│       ├── scenario_4_visa.svg
│       ├── scenario_5_visa.svg
│       ├── scenario_6_visa.svg      # DOB: 1991 (conflict!)
│       └── scenario_7_visa.svg
```

**Note**: SVG files contain embedded metadata in comments for programmatic parsing during demo execution.

---

## Verification Checklist

When demonstrating, verify each scenario produces:

- [ ] Correct case creation with expected case_number pattern
- [ ] Documents processed with correct status
- [ ] Evidence atoms with correct severity, source, freshness
- [ ] Identity graph with expected nodes/edges/conflicts
- [ ] Fusion scores matching expected ranges
- [ ] Correct recommendation tier
- [ ] Audit trail with intact hash chain
- [ ] Sync queue entries for offline scenario (7)

---

## Judge Presentation Tips

### Key Talking Points Per Scenario

| Scenario | Emphasize |
|----------|-----------|
| 1 | Baseline - system works for legitimate travelers |
| 2 | **Expiry detection** - deterministic rule, not ML guess |
| 3 | **Biometric mismatch** - liveness confirms real person, just wrong person |
| 4 | **CONFIRMED_ADVERSE** - authoritative source, not heuristic |
| 5 | **Multi-layer forensics** - ELA + SIFT + font analysis |
| 6 | **Identity graph** - CONFLICTS_WITH edges explain fragmentation |
| 7 | **UNAVAILABLE ≠ CLEAR** - the critical architectural decision |

### Evidence Trail Demo
For each scenario, show:
1. **Evidence View**: All atoms with severity badges
2. **Fusion Breakdown**: Positive/negative contributions
3. **Identity Graph**: Visual conflicts (scenario 6)
4. **Audit Trail**: Hash chain verification
5. **Officer UI**: Recommendation with reasoning

---

## Custom Scenario Creation

To add new scenarios:

1. Add SVG files to `demo_data/faces/` and `demo_data/documents/`
2. Add scenario definition in `configuration/demo_scenarios/scenarios.yaml`
3. Register in `backend/app/api/demo.py` scenario router
4. Add integration test in `tests/integration/test_demo_scenarios.py`

---

## Related Documentation

- [Architecture](architecture.md) - System design
- [API Reference](api.md) - Demo endpoints
- [Limitations](limitations.md) - Known constraints