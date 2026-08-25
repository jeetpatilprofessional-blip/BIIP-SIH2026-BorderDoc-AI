#!/bin/bash
# BIIP-SIH2026 Development Environment Setup Script
# Run this once to set up the complete development environment

set -e  # Exit on error

echo "=========================================="
echo "BIIP-SIH2026 Development Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 found: $($1 --version 2>&1 | head -1)"
    else
        echo -e "${RED}✗${NC} $1 not found - please install it"
        MISSING_DEPS=1
    fi
}

echo ""
echo "Checking prerequisites..."
check_command docker
check_command docker-compose
check_command git
check_command node
check_command npm
check_command python3

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${RED}Missing dependencies. Please install them first.${NC}"
    exit 1
fi

# Check Node version
NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo -e "${YELLOW}⚠ Node.js version $NODE_VERSION < 20, may cause issues${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d. -f1,2)
if [[ "$PYTHON_VERSION" < "3.11" ]]; then
    echo -e "${YELLOW}⚠ Python version $PYTHON_VERSION < 3.11, may cause issues${NC}"
fi

echo ""
echo "=========================================="
echo "Setting up Backend"
echo "=========================================="

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example
if [ ! -f ".env" ]; then
    echo "Creating backend .env from example..."
    cp ../.env.example .env
    echo -e "${YELLOW}⚠ Please edit backend/.env with your settings${NC}"
fi

# Create models directory
mkdir -p models/insightface

# Run database migrations (if using PostgreSQL)
# alembic upgrade head

echo -e "${GREEN}✓ Backend setup complete${NC}"

cd ..

echo ""
echo "=========================================="
echo "Setting up Frontend"
echo "=========================================="

cd frontend

# Install dependencies
echo "Installing Node dependencies..."
npm install

# Create .env from example
if [ ! -f ".env" ]; then
    echo "Creating frontend .env..."
    cat > .env << EOF
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_DEMO_MODE=true
EOF
fi

echo -e "${GREEN}✓ Frontend setup complete${NC}"

cd ..

echo ""
echo "=========================================="
echo "Downloading AI Models (Optional)"
echo "=========================================="

MODEL_DIR="backend/models/insightface"
if [ ! -f "$MODEL_DIR/buffalo_l.onnx" ]; then
    echo "Downloading InsightFace buffalo_l model (~200MB)..."
    mkdir -p "$MODEL_DIR"
    cd "$MODEL_DIR"

    # Try multiple sources
    if command -v wget &> /dev/null; then
        wget -q --show-progress "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip" || \
        wget -q --show-progress "https://insightface.s3.us-west-2.amazonaws.com/buffalo_l.zip"
    elif command -v curl &> /dev/null; then
        curl -L -o buffalo_l.zip "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip" || \
        curl -L -o buffalo_l.zip "https://insightface.s3.us-west-2.amazonaws.com/buffalo_l.zip"
    fi

    if [ -f "buffalo_l.zip" ]; then
        unzip -q buffalo_l.zip
        rm buffalo_l.zip
        echo -e "${GREEN}✓ Model downloaded${NC}"
    else
        echo -e "${YELLOW}⚠ Could not download model - will download on first run${NC}"
    fi

    cd ../../..
else
    echo -e "${GREEN}✓ Model already present${NC}"
fi

echo ""
echo "=========================================="
echo "Starting Services with Docker Compose"
echo "=========================================="

# Start database and other services
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
sleep 5

# Run backend migrations
cd backend
source venv/bin/activate
alembic upgrade head 2>/dev/null || echo "Migrations will run on first API start"
cd ..

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start development servers:"
echo ""
echo "  Terminal 1 - Backend:"
echo "    cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "  Terminal 2 - Frontend:"
echo "    cd frontend && npm run dev"
echo ""
echo "Or use Docker Compose for everything:"
echo "  docker-compose up --build"
echo ""
echo "Access points:"
echo "  Frontend:     http://localhost:3000 (docker) or http://localhost:5173 (dev)"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Database:     localhost:5432 (postgres/postgres)"
echo ""
echo "Run demo scenarios:"
echo "  curl -X POST http://localhost:8000/api/demo/load-test-data"
echo "  curl -X POST http://localhost:8000/api/demo/scenarios/scenario_1/run"
echo ""
echo "Run tests:"
echo "  cd backend && pytest tests/ -v"