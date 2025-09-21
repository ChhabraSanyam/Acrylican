# Production Deployment Guide

This guide covers the complete production deployment process for the Artisan Promotion Platform.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: Minimum 20GB free space
- **Network**: Stable internet connection for external API calls

### Required Accounts and API Keys

1. **Google Gemini API**: For AI content generation
2. **Cloud Storage**: AWS S3, Google Cloud Storage, or Cloudflare R2
3. **Platform APIs**: Facebook, Instagram, Etsy, Pinterest, Shopify (optional)
4. **Monitoring**: Sentry for error tracking (optional)
5. **Email**: SMTP service for notifications (optional)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd artisan-promotion-platform

# Generate secure secrets
./scripts/generate-secrets.sh

# Copy and configure environment
cp .env.production.example .env.production
# Edit .env.production with your actual values
```

### 2. Configure Environment

Edit `.env.production` with your actual values:

```bash
# Database passwords (use generated secrets)
POSTGRES_PASSWORD=your_secure_database_password
REDIS_PASSWORD=your_secure_redis_password

# Application security (use generated secrets)
SECRET_KEY=your_very_long_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_32_character_encryption_key

# External services
GEMINI_API_KEY=your_google_gemini_api_key
CLOUD_STORAGE_BUCKET=your-storage-bucket
CLOUD_STORAGE_ACCESS_KEY=your_access_key
CLOUD_STORAGE_SECRET_KEY=your_secret_key

# Domain configuration
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 3. Deploy

```bash
# Run the deployment script
./scripts/deploy.sh

# Or deploy manually
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment

```bash
# Run deployment tests
./scripts/test-deployment.sh

# Check application status
curl http://localhost:8000/health
curl http://localhost:80/health
```

## Detailed Deployment Process

### Step 1: Server Preparation

#### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

#### 1.2 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 1.3 Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw --force enable
```

### Step 2: Application Setup

#### 2.1 Create Application Directory

```bash
sudo mkdir -p /opt/artisan-platform
sudo chown $USER:$USER /opt/artisan-platform
cd /opt/artisan-platform
```

#### 2.2 Clone Repository

```bash
git clone <repository-url> .
```

#### 2.3 Generate Secrets

```bash
./scripts/generate-secrets.sh
```

This creates `.env.production.secrets` with secure random passwords and keys.

#### 2.4 Configure Environment

```bash
# Copy example environment file
cp .env.production.example .env.production

# Merge generated secrets
cat .env.production.secrets >> .env.production

# Edit with your specific values
nano .env.production
```

### Step 3: Database Setup

#### 3.1 Initialize Database

The database will be automatically initialized when you run the deployment. The initialization includes:

- Creating the database and user
- Installing required PostgreSQL extensions
- Setting up performance optimizations
- Creating audit logging tables

#### 3.2 Run Migrations

Migrations are automatically run during deployment, but you can run them manually:

```bash
docker-compose -f docker-compose.prod.yml run --rm migrate
```

### Step 4: SSL/TLS Configuration (Optional)

#### 4.1 Obtain SSL Certificate

Using Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo apt install -y certbot

# Obtain certificate
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com
```

#### 4.2 Configure SSL in Docker Compose

Update `docker-compose.prod.yml` to mount SSL certificates:

```yaml
frontend:
  volumes:
    - /etc/letsencrypt/live/your-domain.com:/etc/ssl/certs:ro
  environment:
    - SSL_CERT_PATH=/etc/ssl/certs/fullchain.pem
    - SSL_KEY_PATH=/etc/ssl/certs/privkey.pem
```

### Step 5: Deploy Application

#### 5.1 Run Deployment Script

```bash
./scripts/deploy.sh
```

This script will:
1. Check prerequisites
2. Create database backup (if existing)
3. Build Docker images
4. Run database migrations
5. Deploy services
6. Run health checks
7. Clean up old resources

#### 5.2 Manual Deployment (Alternative)

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Step 6: Verify Deployment

#### 6.1 Run Deployment Tests

```bash
./scripts/test-deployment.sh
```

#### 6.2 Manual Verification

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:80/health

# Check detailed health
curl http://localhost:8000/health/detailed

# Check API documentation
curl http://localhost:8000/docs
```

#### 6.3 Check Logs

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# View specific service logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
docker-compose -f docker-compose.prod.yml logs db
```

## Monitoring and Maintenance

### Health Monitoring

The application provides several health check endpoints:

- `/health` - Basic health check
- `/health/detailed` - Comprehensive health check
- `/health/readiness` - Kubernetes readiness probe
- `/health/liveness` - Kubernetes liveness probe

### Log Management

Logs are stored in the `logs/` directory and rotated automatically:

```bash
# View application logs
tail -f logs/deployment.log
tail -f logs/application.log

# View container logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Database Backups

Backups are automatically created during deployment:

```bash
# Manual backup
docker exec artisan-platform-db pg_dump -U artisan_user artisan_platform > backup.sql

# Restore from backup
docker exec -i artisan-platform-db psql -U artisan_user artisan_platform < backup.sql
```

### Updates and Maintenance

#### Update Application

```bash
# Pull latest code
git pull origin main

# Redeploy
./scripts/deploy.sh
```

#### Update Dependencies

```bash
# Update Docker images
docker-compose -f docker-compose.prod.yml pull

# Rebuild with latest base images
docker-compose -f docker-compose.prod.yml build --no-cache
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs [service-name]

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Restart specific service
docker-compose -f docker-compose.prod.yml restart [service-name]
```

#### 2. Database Connection Issues

```bash
# Check database container
docker-compose -f docker-compose.prod.yml logs db

# Test database connection
docker exec -it artisan-platform-db psql -U artisan_user -d artisan_platform

# Check database configuration
grep DATABASE_URL .env.production
```

#### 3. API Not Responding

```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Check if port is accessible
netstat -tlnp | grep :8000

# Test API directly
curl -v http://localhost:8000/health
```

#### 4. Frontend Not Loading

```bash
# Check frontend logs
docker-compose -f docker-compose.prod.yml logs frontend

# Check nginx configuration
docker exec artisan-platform-frontend nginx -t

# Check if port is accessible
netstat -tlnp | grep :80
```

### Performance Issues

#### High Memory Usage

```bash
# Check container resource usage
docker stats

# Check system resources
htop
free -h
df -h
```

#### Slow Response Times

```bash
# Check detailed health metrics
curl http://localhost:8000/health/detailed

# Monitor database performance
docker exec -it artisan-platform-db psql -U artisan_user -d artisan_platform -c "SELECT * FROM pg_stat_activity;"
```

### Recovery Procedures

#### Rollback Deployment

```bash
./scripts/rollback.sh
```

#### Emergency Stop

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Stop and remove everything (CAUTION: This removes data)
docker-compose -f docker-compose.prod.yml down -v
```

## Security Considerations

### 1. Environment Variables

- Never commit `.env.production` to version control
- Use strong, unique passwords for all services
- Rotate secrets regularly
- Use environment-specific secret management in production

### 2. Network Security

- Configure firewall to only allow necessary ports
- Use HTTPS in production
- Implement rate limiting
- Monitor for suspicious activity

### 3. Container Security

- Run containers as non-root users
- Keep base images updated
- Scan images for vulnerabilities
- Use minimal base images

### 4. Database Security

- Use strong passwords
- Enable SSL connections
- Limit database user privileges
- Regular security updates

## CI/CD Integration

### GitHub Actions

The repository includes a GitHub Actions workflow for automated deployment:

1. **Setup Secrets**: Add the following secrets to your GitHub repository:
   - `PRODUCTION_HOST`: Your server IP/hostname
   - `PRODUCTION_USER`: SSH username
   - `PRODUCTION_SSH_KEY`: SSH private key
   - `PRODUCTION_ENV`: Content of your `.env.production` file

2. **Trigger Deployment**: Push to `main` branch or create a release tag

3. **Monitor Deployment**: Check the Actions tab for deployment status

### Manual CI/CD Setup

For other CI/CD systems, use the deployment script:

```bash
# In your CI/CD pipeline
./scripts/deploy.sh --skip-backup --skip-health-check
```

## Scaling and Performance

### Horizontal Scaling

To scale the application:

1. **Load Balancer**: Add a load balancer in front of multiple frontend instances
2. **Database**: Use read replicas for better performance
3. **Redis**: Use Redis Cluster for high availability
4. **File Storage**: Use CDN for static assets

### Vertical Scaling

Adjust resource limits in `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**:
   - Check application logs
   - Monitor resource usage
   - Verify backups

2. **Monthly**:
   - Update dependencies
   - Review security logs
   - Performance optimization

3. **Quarterly**:
   - Security audit
   - Disaster recovery testing
   - Capacity planning

### Getting Help

1. Check application logs first
2. Review this documentation
3. Run deployment tests to identify issues
4. Check GitHub issues for known problems

## Appendix

### Environment Variables Reference

See `.env.production.example` for a complete list of environment variables.

### Port Reference

- **80**: Frontend (HTTP)
- **443**: Frontend (HTTPS, if configured)
- **8000**: Backend API
- **5432**: PostgreSQL (internal)
- **6379**: Redis (internal)

### File Structure

```
/opt/artisan-platform/
├── backend/                 # Backend application
├── frontend/               # Frontend application
├── database/               # Database initialization scripts
├── scripts/                # Deployment and maintenance scripts
├── logs/                   # Application logs
├── backups/               # Database backups
├── docker-compose.prod.yml # Production Docker Compose
└── .env.production        # Production environment variables
```