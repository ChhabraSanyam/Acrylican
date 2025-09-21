# Artisan Platform Production Operations Runbook

## Table of Contents
1. [System Overview](#system-overview)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Incident Response](#incident-response)
4. [Backup and Recovery](#backup-and-recovery)
5. [Scaling Operations](#scaling-operations)
6. [Security Operations](#security-operations)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Emergency Contacts](#emergency-contacts)

## System Overview

### Architecture Components
- **Frontend**: React application served via Nginx
- **Backend**: FastAPI Python application
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis cluster
- **File Storage**: AWS S3 with CloudFront CDN
- **Container Orchestration**: Kubernetes
- **Load Balancer**: AWS Application Load Balancer
- **Monitoring**: Prometheus + Grafana + AlertManager

### Key Metrics to Monitor
- **Application Health**: Response time, error rate, throughput
- **Infrastructure**: CPU, memory, disk usage, network I/O
- **Database**: Connection pool, query performance, replication lag
- **Cache**: Hit rate, memory usage, connection count
- **Business Metrics**: User registrations, posts created, platform connections

## Monitoring and Alerting

### Health Check Endpoints
```bash
# Application health
curl https://api.artisan-platform.com/monitoring/health

# Liveness probe (Kubernetes)
curl https://api.artisan-platform.com/monitoring/health/liveness

# Readiness probe (Kubernetes)
curl https://api.artisan-platform.com/monitoring/health/readiness

# Metrics endpoint
curl https://api.artisan-platform.com/monitoring/metrics
```

### Critical Alerts

#### High Priority (Immediate Response Required)
- **Service Down**: Any core service unavailable for >2 minutes
- **Database Connection Failure**: Cannot connect to primary database
- **High Error Rate**: >5% error rate for >5 minutes
- **Memory Usage**: >90% memory usage for >10 minutes
- **Disk Space**: <10% free disk space

#### Medium Priority (Response within 30 minutes)
- **High Response Time**: >2s average response time for >10 minutes
- **Cache Miss Rate**: >50% cache miss rate for >15 minutes
- **Failed Backups**: Backup job failures
- **SSL Certificate Expiry**: Certificate expires within 7 days

#### Low Priority (Response within 4 hours)
- **High CPU Usage**: >80% CPU usage for >30 minutes
- **Slow Database Queries**: Queries taking >5s
- **File Upload Failures**: >10% file upload failure rate

### Grafana Dashboards
- **System Overview**: High-level system health and performance
- **Application Metrics**: Request rates, response times, error rates
- **Infrastructure**: Server resources, network, storage
- **Database Performance**: Query performance, connections, replication
- **Business Metrics**: User activity, platform usage, revenue

## Incident Response

### Incident Severity Levels

#### Severity 1 (Critical)
- **Definition**: Complete service outage or data loss
- **Response Time**: Immediate (within 15 minutes)
- **Escalation**: Notify on-call engineer and management
- **Communication**: Update status page every 30 minutes

#### Severity 2 (High)
- **Definition**: Significant feature degradation affecting >50% of users
- **Response Time**: Within 1 hour
- **Escalation**: Notify on-call engineer
- **Communication**: Update status page every hour

#### Severity 3 (Medium)
- **Definition**: Minor feature issues affecting <50% of users
- **Response Time**: Within 4 hours
- **Escalation**: Assign to appropriate team
- **Communication**: Internal notification only

### Incident Response Process

1. **Detection**: Alert received or issue reported
2. **Assessment**: Determine severity and impact
3. **Response**: Assign incident commander and response team
4. **Communication**: Update stakeholders and status page
5. **Investigation**: Identify root cause
6. **Resolution**: Implement fix and verify
7. **Post-Incident**: Conduct review and document lessons learned

### Emergency Procedures

#### Complete Service Outage
```bash
# 1. Check overall system status
kubectl get pods -n artisan-platform
kubectl get services -n artisan-platform

# 2. Check ingress and load balancer
kubectl describe ingress artisan-platform-ingress -n artisan-platform

# 3. Check database connectivity
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT 1;"

# 4. Check application logs
kubectl logs -f deployment/artisan-platform-backend -n artisan-platform

# 5. If needed, restart services
kubectl rollout restart deployment/artisan-platform-backend -n artisan-platform
kubectl rollout restart deployment/artisan-platform-frontend -n artisan-platform
```

#### Database Issues
```bash
# Check database status
kubectl exec -it postgres-0 -n artisan-platform -- pg_isready

# Check replication status
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Check slow queries
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# If needed, failover to replica
# (Follow database failover procedure)
```

## Backup and Recovery

### Backup Schedule
- **Database**: Daily at 2:00 AM UTC
- **Redis**: Daily at 3:00 AM UTC  
- **File Storage**: Weekly on Sunday at 4:00 AM UTC
- **Configuration**: Daily with code deployments

### Backup Verification
```bash
# Check backup job status
kubectl get cronjobs -n artisan-platform

# Check latest backup files
aws s3 ls s3://artisan-platform-backups/database/ --recursive | tail -10
aws s3 ls s3://artisan-platform-backups/redis/ --recursive | tail -10

# Test backup integrity
./scripts/backup-restore.sh health-check
```

### Recovery Procedures

#### Database Recovery
```bash
# 1. Stop application to prevent writes
kubectl scale deployment artisan-platform-backend --replicas=0 -n artisan-platform

# 2. Restore from backup
./scripts/backup-restore.sh restore-db s3://artisan-platform-backups/database/postgres_backup_YYYYMMDD_HHMMSS.sql.gz

# 3. Verify data integrity
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT COUNT(*) FROM users;"

# 4. Restart application
kubectl scale deployment artisan-platform-backend --replicas=3 -n artisan-platform
```

#### Complete Disaster Recovery
```bash
# Run full disaster recovery
./scripts/backup-restore.sh disaster-recovery

# Verify all services
kubectl get pods -n artisan-platform
./scripts/backup-restore.sh health-check
```

## Scaling Operations

### Horizontal Pod Autoscaling
```bash
# Check HPA status
kubectl get hpa -n artisan-platform

# View HPA details
kubectl describe hpa artisan-platform-backend-hpa -n artisan-platform

# Manual scaling (if needed)
kubectl scale deployment artisan-platform-backend --replicas=5 -n artisan-platform
```

### Cluster Autoscaling
```bash
# Check cluster autoscaler status
kubectl get deployment cluster-autoscaler -n kube-system

# View autoscaler logs
kubectl logs -f deployment/cluster-autoscaler -n kube-system

# Check node status
kubectl get nodes
kubectl describe nodes
```

### Database Scaling
```bash
# Check database performance
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Scale read replicas (if needed)
kubectl scale statefulset postgres-replica --replicas=2 -n artisan-platform

# Monitor replication lag
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"
```

## Security Operations

### Security Monitoring
```bash
# Check security events
kubectl logs -f deployment/artisan-platform-backend -n artisan-platform | grep "SECURITY EVENT"

# Check failed login attempts
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT * FROM audit_logs WHERE event_type = 'failed_login' AND created_at > NOW() - INTERVAL '1 hour';"

# Check rate limiting
curl -I https://api.artisan-platform.com/auth/login
# Look for X-RateLimit-* headers
```

### Certificate Management
```bash
# Check certificate expiry
kubectl get certificates -n artisan-platform

# Renew certificate (if needed)
kubectl delete certificate tls-secret -n artisan-platform
# cert-manager will automatically renew

# Verify certificate
openssl s_client -connect api.artisan-platform.com:443 -servername api.artisan-platform.com
```

### Security Incident Response
1. **Isolate**: Block suspicious IPs at load balancer level
2. **Investigate**: Check logs for attack patterns
3. **Mitigate**: Apply security patches or configuration changes
4. **Monitor**: Increase monitoring for similar attacks
5. **Report**: Document incident and notify security team

## Troubleshooting Guide

### Common Issues

#### High Response Times
```bash
# Check application metrics
curl https://api.artisan-platform.com/monitoring/metrics

# Check database performance
kubectl exec -it postgres-0 -n artisan-platform -- psql -U postgres -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check cache hit rate
kubectl exec -it redis-0 -n artisan-platform -- redis-cli info stats | grep keyspace
```

#### Memory Leaks
```bash
# Check memory usage
kubectl top pods -n artisan-platform

# Check for memory leaks in application
kubectl exec -it deployment/artisan-platform-backend -n artisan-platform -- ps aux

# Restart affected pods
kubectl delete pod <pod-name> -n artisan-platform
```

#### File Upload Issues
```bash
# Check S3 connectivity
aws s3 ls s3://artisan-platform-files/

# Check file processing service
kubectl logs -f deployment/artisan-platform-backend -n artisan-platform | grep "image_processing"

# Check disk space on nodes
kubectl get nodes -o wide
```

### Log Analysis
```bash
# Application logs
kubectl logs -f deployment/artisan-platform-backend -n artisan-platform --tail=100

# Filter for errors
kubectl logs deployment/artisan-platform-backend -n artisan-platform | grep ERROR

# Database logs
kubectl logs -f postgres-0 -n artisan-platform

# Ingress logs
kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx
```

## Emergency Contacts

### On-Call Rotation
- **Primary**: DevOps Engineer (24/7)
- **Secondary**: Backend Developer (business hours)
- **Escalation**: Engineering Manager

### Contact Information
- **Slack**: #incidents channel
- **PagerDuty**: artisan-platform service
- **Email**: ops@artisan-platform.com
- **Phone**: Emergency hotline (for Severity 1 incidents)

### External Vendors
- **AWS Support**: Business support plan
- **Database Vendor**: PostgreSQL support contract
- **CDN Provider**: CloudFlare support
- **Monitoring**: Grafana Cloud support

## Maintenance Windows

### Scheduled Maintenance
- **Time**: Sunday 2:00-4:00 AM UTC (lowest traffic)
- **Frequency**: Monthly for major updates
- **Notification**: 48 hours advance notice
- **Rollback Plan**: Always prepared before maintenance

### Emergency Maintenance
- **Authorization**: Engineering Manager approval required
- **Communication**: Immediate notification to all stakeholders
- **Documentation**: Post-maintenance report required

## Performance Baselines

### Normal Operating Ranges
- **Response Time**: <500ms (95th percentile)
- **Error Rate**: <1%
- **CPU Usage**: 30-60%
- **Memory Usage**: 40-70%
- **Database Connections**: <80% of pool
- **Cache Hit Rate**: >90%

### Capacity Planning
- **User Growth**: Plan for 50% growth quarterly
- **Storage Growth**: Monitor file storage growth monthly
- **Database Size**: Plan for 100% growth annually
- **Traffic Patterns**: Peak usage during business hours (9 AM - 6 PM local time)

---

**Document Version**: 1.0  
**Last Updated**: $(date)  
**Next Review**: Quarterly  
**Owner**: DevOps Team