# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- PostgreSQL (if not using Docker)
- Redis (if not using Docker)
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

## Quick Start with Docker Compose

1. **Clone and navigate to the project:**
```bash
cd aifai
```

2. **Set up environment variables:**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your configuration
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Access the services:**
- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:3000 (if frontend is added to docker-compose)
- API Documentation: http://localhost:8000/docs

## Manual Setup

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up database:**
```bash
# Create PostgreSQL database
createdb aifai

# Or using psql:
psql -U postgres -c "CREATE DATABASE aifai;"
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your database and Redis URLs
```

4. **Run migrations (tables are auto-created on startup):**
```bash
# The application will create tables automatically on first run
python main.py
```

5. **Start the server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Configure environment:**
Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. **Run development server:**
```bash
npm run dev
```

4. **Build for production:**
```bash
npm run build
npm start
```

## Cloud Deployment

### AWS Deployment

1. **RDS for PostgreSQL:**
   - Create RDS PostgreSQL instance
   - Update `DATABASE_URL` in environment variables

2. **ElastiCache for Redis:**
   - Create ElastiCache Redis cluster
   - Update `REDIS_URL` in environment variables

3. **ECS/Fargate for Backend:**
   - Build Docker image: `docker build -t aifai-backend ./backend`
   - Push to ECR
   - Deploy to ECS/Fargate with environment variables

4. **Amplify/Vercel for Frontend:**
   - Connect GitHub repository
   - Set `NEXT_PUBLIC_API_URL` environment variable
   - Deploy

### Google Cloud Platform

1. **Cloud SQL for PostgreSQL:**
   - Create Cloud SQL instance
   - Update connection string

2. **Cloud Run for Backend:**
   - Build and deploy: `gcloud run deploy aifai-backend --source ./backend`

3. **Cloud Run for Frontend:**
   - Build and deploy: `gcloud run deploy aifai-frontend --source ./frontend`

### Azure Deployment

1. **Azure Database for PostgreSQL:**
   - Create PostgreSQL server
   - Update connection string

2. **Azure Container Instances or App Service:**
   - Deploy backend container
   - Deploy frontend container

## Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/aifai

# Redis
REDIS_URL=redis://host:6379/0

# Security (IMPORTANT: Change in production!)
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# CORS
CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Security Considerations

1. **Change SECRET_KEY:** Generate a strong random secret key for production
2. **Use HTTPS:** Always use HTTPS in production
3. **Database Security:** Use strong passwords and restrict access
4. **CORS:** Configure CORS origins properly
5. **Rate Limiting:** Consider adding rate limiting for production
6. **API Keys:** Store API keys securely (use secrets management)

## Monitoring

Consider adding:
- Application monitoring (e.g., Sentry, Datadog)
- Database monitoring
- Log aggregation (e.g., ELK stack, CloudWatch)
- Health check endpoints (already available at `/health`)

## Scaling

- **Horizontal Scaling:** Run multiple backend instances behind a load balancer
- **Database:** Use connection pooling (already configured)
- **Caching:** Redis is configured for caching
- **CDN:** Use CDN for frontend static assets
