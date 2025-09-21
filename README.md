# Artisan Promotion Platform

A comprehensive solution to help local artisans efficiently promote and sell their handcrafted products across multiple online platforms.

## Features

- AI-powered content generation for product marketing
- Multi-platform posting automation (Facebook, Instagram, Etsy, Pinterest, etc.)
- Comprehensive analytics dashboard
- Secure user authentication and data protection

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

1. Clone the repository
2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
3. Start all services:
   ```bash
   docker-compose up -d
   ```

### Services

- **Frontend**: http://localhost:3000 (React with TypeScript and Tailwind CSS)
- **Backend API**: http://localhost:8000 (FastAPI with automatic docs at /docs)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Local Development

#### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

#### Backend Tests
```bash
cd backend
pytest
```

#### Frontend Tests
```bash
cd frontend
npm test
```

## Project Structure

```
artisan-promotion-platform/
├── backend/                 # FastAPI backend
│   ├── app/                # Application code
│   ├── tests/              # Test files
│   ├── migrations/         # Database migrations
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/               # Source code
│   ├── public/            # Static files
│   └── package.json       # Node.js dependencies
└── docker-compose.yml     # Development environment
```

## Next Steps

1. Configure environment variables in `.env` files
2. Set up external API keys (Gemini, social platforms)
3. Run database migrations
4. Start implementing authentication system