# Production Scaling Guide

## Overview

This guide covers scaling strategies for the Artisan Platform to handle increased traffic, user growth, and data volume. It includes both horizontal and vertical scaling approaches for different components.

## Scaling Architecture

### Current Architecture Limits
- **Frontend**: Stateless, easily scalable
- **Backend**: Stateless API, horizontally scalable
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis cluster
- **File Storage**: Cloud storage (virtually unlimited)
- **Message Queue**: Redis-based queue system

### Scaling Triggers
- **CPU Usage**: >70% average for 10 minutes
- **Memory Usage**: >80% average for 10 minutes
- **Response Time**: >1s 95th percentile for 5 minutes
- **Queue Length**: >100 pending jobs
- **Database Connections**: >80% of pool

## Horizontal Pod Autoscaling (HPA)

### Backend Service Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: artisan-platform-backend-hpa
  namespace: artisan-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: artisan-platform-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 60
      selectPolicy: Max
```

### Frontend Service Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: artisan-platform-frontend-hpa
  namespace: artisan-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: artisan-platform-frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### Queue Worker Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: queue-worker-hpa
  namespace: artisan-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: queue-worker
  minReplicas: 2
  maxReplicas: 15
  metrics:
  - type: External
    external:
      metric:
        name: redis_queue_length
      target:
        type: AverageValue
        averageValue: "10"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Pods
        value: 3
        periodSeconds: 30
```

## Vertical Pod Autoscaling (VPA)

### Backend VPA Configuration

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: artisan-platform-backend-vpa
  namespace: artisan-platform
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: artisan-platform-backend
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: backend
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 4
        memory: 8Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
```

## Database Scaling

### Read Replica Configuration

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: artisan-platform
spec:
  instances: 3
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      maintenance_work_mem: "64MB"
      checkpoint_completion_target: "0.9"
      wal_buffers: "16MB"
      default_statistics_target: "100"
      random_page_cost: "1.1"
      effective_io_concurrency: "200"
  
  bootstrap:
    initdb:
      database: artisan_platform
      owner: app_user
      secret:
        name: postgres-credentials
  
  storage:
    size: 100Gi
    storageClass: gp3
  
  monitoring:
    enabled: true
  
  backup:
    retentionPolicy: "30d"
    barmanObjectStore:
      destinationPath: "s3://artisan-platform-backups/postgres"
      s3Credentials:
        accessKeyId:
          name: backup-credentials
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: backup-credentials
          key: SECRET_ACCESS_KEY
      wal:
        retention: "7d"
      data:
        retention: "30d"
```

### Connection Pooling with PgBouncer

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
  namespace: artisan-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    metadata:
      labels:
        app: pgbouncer
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        ports:
        - containerPort: 5432
        env:
        - name: DATABASES_HOST
          value: postgres-cluster-rw
        - name: DATABASES_PORT
          value: "5432"
        - name: DATABASES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: username
        - name: DATABASES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
        - name: DATABASES_DBNAME
          value: artisan_platform
        - name: POOL_MODE
          value: transaction
        - name: MAX_CLIENT_CONN
          value: "1000"
        - name: DEFAULT_POOL_SIZE
          value: "25"
        - name: MIN_POOL_SIZE
          value: "5"
        - name: RESERVE_POOL_SIZE
          value: "5"
        - name: SERVER_RESET_QUERY
          value: "DISCARD ALL"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

## Redis Scaling

### Redis Cluster Configuration

```yaml
apiVersion: redis.redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: redis-cluster
  namespace: artisan-platform
spec:
  clusterSize: 6
  clusterVersion: v7.0.5
  persistenceEnabled: true
  
  redisExporter:
    enabled: true
    image: oliver006/redis_exporter:latest
  
  storage:
    volumeClaimTemplate:
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 20Gi
  
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 1Gi
  
  redisConfig:
    maxmemory: "768mb"
    maxmemory-policy: "allkeys-lru"
    save: "900 1 300 10 60 10000"
    tcp-keepalive: "60"
    timeout: "300"
```

## Cluster Autoscaling

### Node Groups Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-status
  namespace: kube-system
data:
  nodes.max: "50"
  nodes.min: "3"
  scale-down-delay-after-add: "10m"
  scale-down-unneeded-time: "10m"
  scale-down-utilization-threshold: "0.5"
```

### AWS Auto Scaling Groups

```bash
# Create node groups for different workload types

# General purpose nodes
aws eks create-nodegroup \
  --cluster-name artisan-platform \
  --nodegroup-name general-purpose \
  --instance-types t3.medium,t3.large \
  --ami-type AL2_x86_64 \
  --capacity-type ON_DEMAND \
  --scaling-config minSize=2,maxSize=20,desiredSize=3 \
  --subnets subnet-12345,subnet-67890

# Compute optimized for backend processing
aws eks create-nodegroup \
  --cluster-name artisan-platform \
  --nodegroup-name compute-optimized \
  --instance-types c5.large,c5.xlarge \
  --ami-type AL2_x86_64 \
  --capacity-type SPOT \
  --scaling-config minSize=0,maxSize=10,desiredSize=0 \
  --subnets subnet-12345,subnet-67890

# Memory optimized for database and cache
aws eks create-nodegroup \
  --cluster-name artisan-platform \
  --nodegroup-name memory-optimized \
  --instance-types r5.large,r5.xlarge \
  --ami-type AL2_x86_64 \
  --capacity-type ON_DEMAND \
  --scaling-config minSize=1,maxSize=5,desiredSize=2 \
  --subnets subnet-12345,subnet-67890
```

## Load Balancing

### Application Load Balancer Configuration

```yaml
apiVersion: v1
kind: Service
metadata:
  name: artisan-platform-backend-nlb
  namespace: artisan-platform
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: http
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-connection-draining-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-connection-draining-timeout: "60"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: artisan-platform-backend
```

### Ingress with Multiple Backends

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: artisan-platform-ingress
  namespace: artisan-platform
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"
    nginx.ingress.kubernetes.io/load-balance: "round_robin"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "5"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  rules:
  - host: api.artisan-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: artisan-platform-backend
            port:
              number: 8000
```

## CDN and Caching

### CloudFront Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudfront-config
  namespace: artisan-platform
data:
  distribution.json: |
    {
      "CallerReference": "artisan-platform-cdn",
      "Comment": "CDN for Artisan Platform static assets",
      "DefaultCacheBehavior": {
        "TargetOriginId": "S3-artisan-platform-files",
        "ViewerProtocolPolicy": "redirect-to-https",
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        "Compress": true
      },
      "Origins": {
        "Quantity": 2,
        "Items": [
          {
            "Id": "S3-artisan-platform-files",
            "DomainName": "artisan-platform-files.s3.amazonaws.com",
            "S3OriginConfig": {
              "OriginAccessIdentity": ""
            }
          },
          {
            "Id": "API-artisan-platform",
            "DomainName": "api.artisan-platform.com",
            "CustomOriginConfig": {
              "HTTPPort": 443,
              "HTTPSPort": 443,
              "OriginProtocolPolicy": "https-only"
            }
          }
        ]
      },
      "CacheBehaviors": {
        "Quantity": 1,
        "Items": [
          {
            "PathPattern": "/api/*",
            "TargetOriginId": "API-artisan-platform",
            "ViewerProtocolPolicy": "https-only",
            "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
            "TTL": 0
          }
        ]
      }
    }
```

## Performance Optimization

### Application-Level Optimizations

```python
# Backend optimizations for scaling
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ScalableService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.cache = {}
    
    @lru_cache(maxsize=1000)
    async def get_cached_data(self, key: str):
        """Cache frequently accessed data"""
        return await self._fetch_data(key)
    
    async def process_batch(self, items: list, batch_size: int = 100):
        """Process items in batches to avoid overwhelming resources"""
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            await asyncio.gather(*[self.process_item(item) for item in batch])
    
    async def process_with_circuit_breaker(self, func, *args, **kwargs):
        """Implement circuit breaker pattern for external services"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log error and return cached result or default
            return self._get_fallback_result()
```

### Database Query Optimization

```sql
-- Create indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_posts_user_id_created_at 
ON posts (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_products_user_id_status 
ON products (user_id, status) WHERE status = 'active';

CREATE INDEX CONCURRENTLY idx_sale_events_platform_occurred_at 
ON sale_events (platform, occurred_at DESC);

-- Optimize queries with proper indexing
EXPLAIN ANALYZE SELECT * FROM posts 
WHERE user_id = $1 
ORDER BY created_at DESC 
LIMIT 20;

-- Use materialized views for complex aggregations
CREATE MATERIALIZED VIEW user_analytics AS
SELECT 
    user_id,
    COUNT(*) as total_posts,
    SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published_posts,
    AVG(engagement_score) as avg_engagement
FROM posts 
GROUP BY user_id;

-- Refresh materialized view periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY user_analytics;
```

## Monitoring Scaling Events

### Custom Metrics for Scaling

```python
from prometheus_client import Counter, Histogram, Gauge

# Scaling metrics
scaling_events = Counter('scaling_events_total', 'Total scaling events', ['component', 'direction'])
resource_usage = Gauge('resource_usage_percent', 'Resource usage percentage', ['resource', 'component'])
queue_length = Gauge('queue_length', 'Current queue length', ['queue_name'])
response_time = Histogram('response_time_seconds', 'Response time in seconds', ['endpoint'])

# Track scaling events
def track_scaling_event(component: str, direction: str):
    scaling_events.labels(component=component, direction=direction).inc()

# Monitor resource usage
def update_resource_metrics():
    import psutil
    resource_usage.labels(resource='cpu', component='node').set(psutil.cpu_percent())
    resource_usage.labels(resource='memory', component='node').set(psutil.virtual_memory().percent)
```

### Scaling Alerts

```yaml
groups:
- name: scaling.rules
  rules:
  - alert: HighCPUUsage
    expr: avg(rate(container_cpu_usage_seconds_total[5m])) by (pod) > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage detected"
      description: "Pod {{ $labels.pod }} has high CPU usage"
  
  - alert: ScalingEventFrequent
    expr: increase(scaling_events_total[10m]) > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Frequent scaling events"
      description: "Too many scaling events in the last 10 minutes"
  
  - alert: MaxReplicasReached
    expr: kube_deployment_status_replicas / kube_deployment_spec_replicas > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Deployment near maximum replicas"
      description: "Deployment {{ $labels.deployment }} is near maximum replicas"
```

## Scaling Procedures

### Manual Scaling Commands

```bash
# Scale backend deployment
kubectl scale deployment artisan-platform-backend --replicas=10 -n artisan-platform

# Scale frontend deployment
kubectl scale deployment artisan-platform-frontend --replicas=5 -n artisan-platform

# Scale queue workers
kubectl scale deployment queue-worker --replicas=8 -n artisan-platform

# Check scaling status
kubectl get hpa -n artisan-platform
kubectl top pods -n artisan-platform
```

### Emergency Scaling Procedure

```bash
#!/bin/bash
# Emergency scaling script

echo "Starting emergency scaling procedure..."

# Scale critical services immediately
kubectl scale deployment artisan-platform-backend --replicas=15 -n artisan-platform
kubectl scale deployment queue-worker --replicas=12 -n artisan-platform

# Add more nodes if needed
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name artisan-platform-nodes \
  --desired-capacity 10

# Monitor scaling progress
watch kubectl get pods -n artisan-platform

echo "Emergency scaling completed"
```

## Cost Optimization

### Spot Instance Usage

```yaml
apiVersion: v1
kind: Node
metadata:
  labels:
    node-type: spot
    workload: batch-processing
spec:
  taints:
  - key: spot-instance
    value: "true"
    effect: NoSchedule
```

### Resource Requests and Limits

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: artisan-platform-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      nodeSelector:
        node-type: general-purpose
      tolerations:
      - key: spot-instance
        operator: Equal
        value: "true"
        effect: NoSchedule
```

## Testing Scaling

### Load Testing

```bash
# Install k6 for load testing
brew install k6

# Run load test
k6 run --vus 100 --duration 10m load-test.js
```

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  let response = http.get('https://api.artisan-platform.com/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

---

**Document Version**: 1.0  
**Last Updated**: $(date)  
**Next Review**: Quarterly  
**Owner**: DevOps Team