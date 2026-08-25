# Border Identity Intelligence Platform (BIIP)

**Smart India Hackathon 2026 — Offline-First, Person-Centric Border Identity Screening**

---

## Overview

BIIP is an officer-assistance platform for border checkpoints that connects document, biometric, consistency, journey/status, and authoritative-data evidence into an explainable screening recommendation.

**Core Innovation:**
- **Person-Centric Cross-Document Identity Graph** — connects Passport ↔ Visa ↔ National ID ↔ Driving Licence ↔ Face ↔ Permit ↔ Travel Events
- **Explainable Evidence Fusion** — additive evidence trail with signed contributions, not a black-box score
- **Offline-First, Freshness-Aware Verification** — distinguishes VERIFIED_FRESH / VERIFIED_STALE / UNAVAILABLE / CONFIRMED_ADVERSE

> **The system is an OFFICER-ASSISTANCE PLATFORM.** It does NOT autonomously make immigration, detention, refusal, or deportation decisions. The authorized border officer remains the final decision-maker.

---

## Architecture

```
OFFICER
   ↓
DOCUMENT / FACE CAPTURE
   ↓
CAPTURE QUALITY CHECK
   ↓
DOCUMENT IDENTIFICATION
   ↓
DOCUMENT INTELLIGENCE
   ├── OCR
   ├── MRZ
   ├── QR/BARCODE
   ├── DOCUMENT VALIDATION
   └── TAMPER ANALYSIS
   ↓
BIOMETRIC INTELLIGENCE
   ├── FACE DETECTION
   ├── FACE QUALITY
   ├── FACE VERIFICATION
   └── LIVENESS PROTOTYPE
   ↓
CROSS-DOCUMENT IDENTITY GRAPH
   ↓
JOURNEY / RULE / STATUS INTELLIGENCE
   ├── VISA RULES
   ├── PERMIT RULES
   ├── TRAVEL CHRONOLOGY
   ├── WATCHLIST/REVOCATION STATUS
   └── DATA FRESHNESS
   ↓
EVIDENCE ATOM GENERATION
   ↓
EVIDENCE FUSION ENGINE
   ↓
EXPLAINABLE SCREENING RECOMMENDATION
   ↓
BORDER OFFICER
   ↓
AUDIT TRAIL
   ↓
SECURE SYNCHRONIZATION WHEN CONNECTIVITY RETURNS
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Vite + Tailwind CSS + React Flow |
| Backend | Python + FastAPI + Pydantic + SQLModel |
| Database | SQLite (prototype) |
| AI/CV | PaddleOCR / Tesseract, OpenCV, pyzbar, InsightFace (ONNX) |
| Deployment | Docker Compose |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

---

## Project Structure

```
BIIP-SIH2026/
├── frontend/              # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Page components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── services/      # API clients
│   │   ├── types/         # TypeScript types
│   │   └── utils/         # Utilities
│   └── package.json
│
├── backend/               # FastAPI + Python
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Core config, security
│   │   ├── models/        # SQLModel database models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic services
│   │   │   ├── ocr/           # OCR extraction
│   │   │   ├── document/      # Document validation
│   │   │   ├── tamper/        # Tampering detection
│   │   │   ├── biometric/     # Face verification + liveness
│   │   │   ├── identity_graph/# Cross-document graph
│   │   │   ├── evidence/      # Evidence atoms + fusion
│   │   │   ├── freshness/     # Freshness-aware verification
│   │   │   ├── rules/         # Config-driven validation rules
│   │   │   └── sync/          # Offline sync
│   │   └── main.py
│   └── requirements.txt
│
├── demo_data/             # Test images & scenarios
├── tests/                 # Unit, integration, demo tests
├── docs/                  # Architecture, API, limitations, etc.
├── scripts/               # Utility scripts
├── configuration/         # Rules, templates, demo scenarios
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Key Features

### Required PS Modules (Implemented)
1. **OCR Extraction** — Structured field extraction with confidence scores
2. **Document Validation** — Configurable rule-based validation
3. **Tampering Detection** — Cross-field consistency + image analysis + photo comparison
4. **Face Verification** — Detection, quality, embedding, comparison, prototype liveness

### Core Differentiators
- **Cross-Document Identity Graph** — Real consistency reasoning across documents
- **Evidence Atom Engine** — Structured, signed evidence from every subsystem
- **Freshness-Aware Verification** — Four-state freshness: VERIFIED_FRESH / VERIFIED_STALE / UNAVAILABLE / CONFIRMED_ADVERSE
- **Offline-First Operation** — All local functions continue without connectivity
- **Explainable Evidence Fusion** — Additive evidence trail → LOW_CONCERN / SECONDARY_INSPECTION / HIGH_CONCERN / INSUFFICIENT_EVIDENCE

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture & data flow |
| [API Reference](docs/api.md) | REST API endpoints |
| [Database Schema](docs/database.md) | SQLite schema |
| [Demo Guide](docs/demo.md) | Running deterministic demo scenarios |
| [Limitations](docs/limitations.md) | Honest capability boundaries |
| [Teammate Setup](docs/teammate_setup.md) | Onboarding guide |
| [Security & Privacy](docs/security_privacy.md) | Threat model & data handling |

---

## Demo Scenarios

The `configuration/demo_scenarios/` and `demo_data/` folders contain one-click deterministic test cases:

| Scenario | Description |
|----------|-------------|
| `genuine` | All documents consistent, valid, fresh |
| `altered_dob` | Visa DOB differs from passport |
| `altered_number` | Passport number mismatch across docs |
| `photo_tampering` | Document photo replaced |
| `impostor` | Live face doesn't match document |
| `multiple_identity` | Same face, different names across docs |
| `stale_watchlist` | Offline with stale authoritative data |
| `unavailable_status` | Offline — no central verification |

---

## License

SIH 2026 Project — Educational/Research Use

---

## Disclaimer

**This is a student prototype for Smart India Hackathon 2026.**

- No real government database integration
- No certified biometric performance (iBeta)
- No forensic-grade document authentication
- All "central verification" is simulated and clearly labeled
- Liveness detection is PROTOTYPE-LEVEL only
- Production deployment requires certified hardware, vetted models, and government authorization