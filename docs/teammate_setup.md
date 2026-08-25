# BIIP-SIH2026 Teammate Setup Guide

## Quick Start (5 minutes)

### Prerequisites
- **Docker Desktop** (Windows/Mac) or Docker Engine + Compose (Linux)
- **Git** 
- **Node.js 20+** (for frontend development)
- **Python 3.11+** (for backend development)
- **Make** (optional, for convenience commands)

### One-Command Startup
```bash
# Clone and start everything
git clone <repo-url>
cd BIIP-SIH2026
docker-compose up --build
```

**Access Points**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432 (postgres/postgres)

---

## Detailed Setup

### 1. Repository Structure
```
BIIP-SIH2026/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Config, database
│   │   ├── models/         # SQLModel models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   └── lib/            # Utilities, API client
│   ├── package.json
│   └── Dockerfile
├── demo_data/              # Synthetic test data (SVGs)
├── tests/                  # Unit + integration tests
├── docs/                   # Documentation
├── configuration/          # Config files
└── scripts/                # Utility scripts
```

### 2. Backend Development Setup

#### Option A: Docker (Recommended)
```bash
cd backend
docker build -t biip-backend .
docker run -p 8000:8000 -v $(pwd):/app biip-backend
```

#### Option B: Local Python (Faster iteration)
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp ../.env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Seed demo data (optional)
python -m app.db.seed

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Backend Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/biip
# For SQLite dev: DATABASE_URL=sqlite:///./biip.db

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Central Services (simulated in demo)
CENTRAL_API_URL=http://central:8080
CENTRAL_API_KEY=demo-key

# Models
INSIGHTFACE_MODEL_PATH=/app/models/insightface
TESSERACT_CMD=tesseract

# Demo
DEMO_MODE=true
```

### 3. Frontend Development Setup

#### Option A: Docker
```bash
cd frontend
docker build -t biip-frontend .
docker run -p 3000:80 biip-frontend
```

#### Option B: Local Node (Faster iteration)
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Access**: http://localhost:5173 (Vite dev server with HMR)

#### Frontend Environment Variables (.env)
```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_DEMO_MODE=true
```

### 4. Database Setup

#### PostgreSQL (Production-like)
```bash
# Via docker-compose (includes PostgreSQL)
docker-compose up -d postgres

# Or standalone
docker run -d \
  --name biip-postgres \
  -e POSTGRES_DB=biip \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15
```

#### SQLite (Zero-config Development)
```bash
# Set in backend/.env
DATABASE_URL=sqlite:///./biip.db

# Run migrations
cd backend
alembic upgrade head
```

### 5. Model Downloads (Face Verification)

The InsightFace models are downloaded automatically on first run. For offline setup:

```bash
# Backend downloads models to ./models/insightface/
# Pre-download for air-gapped environments:
mkdir -p backend/models/insightface
cd backend/models/insightface

# Download from InsightFace model zoo
# buffalo_l (recommended): ~200MB
wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
unzip buffalo_l.zip
```

---

## Running Tests

### All Tests
```bash
# Backend tests
cd backend
pytest tests/ -v --tb=short

# Frontend tests
cd frontend
npm test
```

### Specific Test Suites
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Test Database
Tests use in-memory SQLite by default (see `tests/conftest.py`).

---

## Development Workflow

### 1. Making Changes

#### Backend
```bash
# 1. Make changes to code
# 2. Run tests
pytest tests/unit/test_your_module.py -v

# 3. Check types (if using mypy)
mypy app/

# 4. Format code
black app/
isort app/
```

#### Frontend
```bash
# 1. Make changes
# 2. Type check
npm run type-check

# 3. Lint
npm run lint

# 4. Format
npm run format
```

### 2. Adding a New Feature

#### Backend Checklist
- [ ] Add models in `app/models/`
- [ ] Add schemas in `app/schemas/`
- [ ] Add service logic in `app/services/`
- [ ] Add API routes in `app/api/`
- [ ] Write unit tests in `tests/unit/`
- [ ] Write integration tests in `tests/integration/`
- [ ] Update OpenAPI docs (auto-generated)

#### Frontend Checklist
- [ ] Add types in `src/types/`
- [ ] Add API calls in `src/lib/api.ts`
- [ ] Create components in `src/components/`
- [ ] Create pages in `src/pages/`
- [ ] Add to routing in `App.tsx`

### 3. Database Migrations

```bash
cd backend

# Create migration after model changes
alembic revision --autogenerate -m "description of change"

# Review generated file in alembic/versions/
# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Demo Scenario Testing

### Run All Scenarios
```bash
# Via API
curl -X POST http://localhost:8000/api/demo/load-test-data
for i in {1..7}; do
  curl -X POST http://localhost:8000/api/demo/scenarios/scenario_$i/run
done
```

### Via Frontend
1. Open http://localhost:3000 (or 5173)
2. Navigate to **Demo Lab**
3. Select scenario and click **Run**

### Expected Results
| Scenario | Recommendation | Key Evidence |
|----------|---------------|--------------|
| 1 Clean Traveler | LOW_CONCERN | All VERIFIED_FRESH |
| 2 Expired Passport | HIGH_CONCERN | CRITICAL expiry |
| 3 Face Mismatch | HIGH_CONCERN | HIGH face mismatch |
| 4 Watchlist Hit | HIGH_CONCERN | CONFIRMED_ADVERSE |
| 5 Document Tampering | HIGH_CONCERN | CRITICAL tamper |
| 6 Identity Fragmentation | SECONDARY_INSPECTION | HIGH conflicts |
| 7 Offline Mode | INSUFFICIENT_EVIDENCE | UNAVAILABLE central |

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Port 8000 in use → change port in docker-compose.yml
# 2. Database connection failed → check DATABASE_URL
# 3. Model download failed → check INSIGHTFACE_MODEL_PATH
```

### Frontend Build Fails
```bash
# Clear cache
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 20+
```

### Database Migration Errors
```bash
# Reset database (development only!)
cd backend
rm biip.db  # If SQLite
alembic upgrade head

# Or with PostgreSQL
docker-compose down -v  # Removes volumes
docker-compose up -d postgres
alembic upgrade head
```

### Face Verification Slow/Errors
```bash
# Check model loaded
curl http://localhost:8000/system/status

# Models should show "loaded"
# If not, check backend logs for download errors
```

### Tests Failing
```bash
# Run specific failing test with more output
pytest tests/unit/test_freshness_engine.py::TestFreshnessEngine::test_fresh_unavailable -xvs

# Check test database setup in tests/conftest.py
```

---

## IDE Configuration

### VS Code (Recommended)

#### Extensions
- Python (Microsoft)
- Pylance
- TypeScript Hero
- ESLint
- Prettier
- Docker
- SQLTools (PostgreSQL driver)

#### Settings (`.vscode/settings.json`)
```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  },
  "typescript.tsdk": "./frontend/node_modules/typescript/lib"
}
```

#### Launch Configurations (`.vscode/launch.json`)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    },
    {
      "name": "Frontend: Vite",
      "type": "node",
      "request": "launch",
      "command": "npm run dev",
      "cwd": "${workspaceFolder}/frontend"
    }
  ]
}
```

### PyCharm / IntelliJ
- Mark `backend/` as sources root
- Configure Python interpreter to venv
- Enable SQLModel/SQLAlchemy support
- Run configurations for pytest, uvicorn

---

## Useful Commands

### Docker
```bash
# Build all
docker-compose build

# Start all (detached)
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart single service
docker-compose restart backend
```

### Database
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d biip

# Run SQL file
docker-compose exec -T postgres psql -U postgres -d biip < script.sql

# Backup
docker-compose exec postgres pg_dump -U postgres biip > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres biip < backup.sql
```

### Backend Shell
```bash
# Access backend container
docker-compose exec backend bash

# Run Python shell
docker-compose exec backend python -c "from app.core.database import engine; print('DB OK')"

# Run management commands
docker-compose exec backend python -m app.db.seed
```

---

## Common Development Tasks

### Add New Document Type
1. Add enum value in `app/models/document.py`
2. Add parser in `app/services/document/validator.py`
3. Add template in `configuration/document_templates/`
4. Add demo scenario if needed
5. Write tests

### Add New Rule
1. Define rule in `configuration/rules/`
2. Add rule type in `app/services/rules/models.py`
3. Implement evaluation in `app/services/rules/engine.py`
4. Register in active rule set
5. Write tests

### Add New Evidence Type
1. Add enum in `app/models/evidence.py`
2. Add generation logic in `app/services/evidence/atoms.py`
3. Update fusion weights in `app/services/evidence/fusion.py`
4. Write tests

### Modify Fusion Weights
Edit `app/services/evidence/fusion.py`:
```python
SEVERITY_WEIGHTS = {
    EvidenceSeverity.INFO: 0.1,
    EvidenceSeverity.LOW: 0.25,
    EvidenceSeverity.MEDIUM: 0.5,
    EvidenceSeverity.HIGH: 0.75,
    EvidenceSeverity.CRITICAL: 1.0,
}

SOURCE_RELIABILITY = {
    EvidenceSource.MRZ: 1.0,
    EvidenceSource.BARCODE: 0.9,
    EvidenceSource.OCR: 0.7,
    # ...
}
```

---

## Code Style Guide

### Python (Backend)
- **Formatter**: Black (line length 100)
- **Imports**: isort (black profile)
- **Types**: Full type hints, Pydantic v2
- **Naming**: snake_case, PascalCase for classes
- **Docstrings**: Google style for public APIs

### TypeScript (Frontend)
- **Formatter**: Prettier (single quotes, trailing commas)
- **Linting**: ESLint (Airbnb + TypeScript)
- **Types**: Strict mode, no `any`
- **Naming**: camelCase, PascalCase for components
- **Components**: Functional + hooks only

### Git
```bash
# Branch naming
feature/short-description
fix/short-description
docs/short-description

# Commit messages (Conventional Commits)
feat: add face verification service
fix: handle expired passport edge case
docs: update API reference
test: add unit tests for fusion engine
refactor: simplify evidence atom generation
```

---

## Getting Help

### Documentation
- [Architecture](architecture.md)
- [API Reference](api.md)
- [Database Schema](database.md)
- [Demo Scenarios](demo.md)
- [Limitations](limitations.md)
- [Security](security_privacy.md)

### Internal Resources
- API Docs: http://localhost:8000/docs (Swagger UI)
- API Docs: http://localhost:8000/redoc (ReDoc)
- Database: Check `alembic/versions/` for schema history

### Key Files to Understand First
1. `backend/app/main.py` - App entry point
2. `backend/app/core/config.py` - Configuration
3. `backend/app/services/evidence/fusion.py` - Core fusion logic
4. `backend/app/services/freshness/engine.py` - Freshness model
5. `backend/app/services/identity_graph/builder.py` - Graph construction
6. `frontend/src/App.tsx` - Frontend routing
7. `frontend/src/pages/Screening.tsx` - Main officer interface

---

## Contributing to SIH2026 Submission

### Demo Preparation Checklist
- [ ] All 7 scenarios run correctly
- [ ] Frontend shows evidence, graph, audit for each
- [ ] No console errors in browser
- [ ] API responds within 2s for demo scenarios
- [ ] Hash chain verification passes
- [ ] Offline mode shows UNAVAILABLE correctly

### Presentation Tips
1. Start with Scenario 1 (clean) - show happy path
2. Show Scenario 4 (watchlist) - emphasize CONFIRMED_ADVERSE
3. Show Scenario 7 (offline) - emphasize UNAVAILABLE ≠ CLEAR
4. Walk through Evidence View → Fusion → Graph → Audit
5. Highlight: "Every recommendation is explainable"

---

## License & Credits

**Smart India Hackathon 2026 Submission**

### Third-Party Libraries (Key)
- FastAPI, SQLModel, Pydantic
- Tesseract OCR, OpenCV, pyzbar
- InsightFace (ONNX Runtime)
- React, TypeScript, Vite, Tailwind CSS
- Cytoscape.js (graph visualization)

See `backend/requirements.txt` and `frontend/package.json` for complete lists.