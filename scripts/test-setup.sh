#!/bin/bash

# Test setup script to verify core dependencies and build system configuration

set -e

echo "🔧 Testing Artisan Promotion Platform Setup..."

# Test Backend
echo "📦 Testing Backend Configuration..."
cd backend

echo "  ✓ Testing Python imports..."
python -c "from app.main import app; from app.config import settings; from app.database import get_db; print('Backend imports successful')"

echo "  ✓ Running backend tests..."
python -m pytest tests/ -v --tb=short

echo "  ✓ Testing FastAPI startup..."
python -c "from app.main import app; print('FastAPI app created successfully')"

cd ..

# Test Frontend
echo "📦 Testing Frontend Configuration..."
cd frontend

echo "  ✓ Testing TypeScript compilation..."
npx tsc --noEmit

echo "  ✓ Running frontend tests..."
npm test

echo "  ✓ Testing build process..."
npm run build

cd ..

echo "✅ All tests passed! Core dependencies and build system are properly configured."
echo ""
echo "🚀 Next steps:"
echo "  1. Start the backend: cd backend && uvicorn app.main:app --reload"
echo "  2. Start the frontend: cd frontend && npm start"
echo "  3. Visit http://localhost:3000 to see the application"