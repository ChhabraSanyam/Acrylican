# Production Monitoring Setup Guide

## Overview

This guide covers the complete setup of production monitoring for the Artisan Platform, including Prometheus, Grafana, AlertManager, and log aggregation.

## Prerequisites

- Kubernetes cluster with RBAC enabled
- Helm 3.x installed
- kubectl configured for the cluster
- Storage class available for persistent volumes

## Monitoring Stack Components

### 1. Prometheus (Metrics Collection)
- Collects metrics from applications and infrastructure
- Stores time-series data
- Provides query language (PromQL)

### 2. Grafana (Visualization)
- Creates dashboards and visualizations
- Alerting and notification management
- User access control

### 3. AlertManager (Alert Routing)
- Handles alerts from Prometheus
- Routes notifications to appropriate channels
- Alert grouping and silencing

### 4. Node Exporter (System Metrics)
- Collects hardware and OS metrics
- CPU, memory, disk, network statistics

### 5. Blackbox Exporter (Endpoint Monitoring)
- HTTP/HTTPS endpoint monitoring
- SSL certificate monitoring
- DNS resolution monitoring

## Installation Steps

### Step 1: Create Monitoring Namespace

```bash
kubectl create namespace monitoring
```

### Step 2: Install Prometheus Stack

```bash
# Add Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values prometheus-values.yaml
```

### Step 3: Configure Prometheus Values

Create `prometheus-values.yaml`:

```yaml
# Prometheus configuration
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp2
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    
    # Service monitor selector
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    
    # External labels
    externalLabels:
      cluster: artisan-platform-prod
      environment: production
    
    # Additional scrape configs
    additionalScrapeConfigs:
      - job_name: 'artisan-platform-backend'
        static_configs:
          - targets: ['artisan-platform-backend:8000']
        metrics_path: '/monitoring/metrics'
        scrape_interval: 30s
      
      - job_name: 'artisan-platform-frontend'
        static_configs:
          - targets: ['artisan-platform-frontend:3000']
        metrics_path: '/metrics'
        scrape_interval: 30s

# Grafana configuration
grafana:
  adminPassword: "secure-admin-password"
  
  persistence:
    enabled: true
    storageClassName: gp2
    size: 10Gi
  
  # Grafana configuration
  grafana.ini:
    server:
      root_url: https://grafana.artisan-platform.com
    security:
      admin_user: admin
      admin_password: secure-admin-password
    auth:
      disable_login_form: false
    auth.anonymous:
      enabled: false
  
  # Data sources
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
        - name: Prometheus
          type: prometheus
          url: http://prometheus-kube-prometheus-prometheus:9090
          access: proxy
          isDefault: true
        - name: Loki
          type: loki
          url: http://loki:3100
          access: proxy

# AlertManager configuration
alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: gp2
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
    
    # Alert routing configuration
    configSecret: alertmanager-config

# Node exporter
nodeExporter:
  enabled: true

# Kube state metrics
kubeStateMetrics:
  enabled: true
```

### Step 4: Configure AlertManager

Create AlertManager configuration:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-config
  namespace: monitoring
stringData:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'alerts@artisan-platform.com'
      smtp_auth_username: 'alerts@artisan-platform.com'
      smtp_auth_password: 'app-password'
    
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'default'
      routes:
        - match:
            severity: critical
          receiver: 'critical-alerts'
        - match:
            severity: warning
          receiver: 'warning-alerts'
    
    receivers:
      - name: 'default'
        email_configs:
          - to: 'ops@artisan-platform.com'
            subject: '[ALERT] {{ .GroupLabels.alertname }}'
            body: |
              {{ range .Alerts }}
              Alert: {{ .Annotations.summary }}
              Description: {{ .Annotations.description }}
              Labels: {{ range .Labels.SortedPairs }}{{ .Name }}={{ .Value }} {{ end }}
              {{ end }}
      
      - name: 'critical-alerts'
        email_configs:
          - to: 'ops@artisan-platform.com,management@artisan-platform.com'
            subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
            body: |
              CRITICAL ALERT - Immediate attention required!
              
              {{ range .Alerts }}
              Alert: {{ .Annotations.summary }}
              Description: {{ .Annotations.description }}
              Severity: {{ .Labels.severity }}
              Service: {{ .Labels.service }}
              Time: {{ .StartsAt }}
              {{ end }}
        slack_configs:
          - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
            channel: '#incidents'
            title: 'Critical Alert: {{ .GroupLabels.alertname }}'
            text: |
              {{ range .Alerts }}
              {{ .Annotations.summary }}
              {{ .Annotations.description }}
              {{ end }}
      
      - name: 'warning-alerts'
        email_configs:
          - to: 'ops@artisan-platform.com'
            subject: '[WARNING] {{ .GroupLabels.alertname }}'
            body: |
              {{ range .Alerts }}
              Alert: {{ .Annotations.summary }}
              Description: {{ .Annotations.description }}
              {{ end }}
```

### Step 5: Create Custom Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: artisan-platform-alerts
  namespace: monitoring
  labels:
    prometheus: kube-prometheus
    role: alert-rules
spec:
  groups:
    - name: artisan-platform.rules
      rules:
        # Application availability
        - alert: ServiceDown
          expr: up{job="artisan-platform-backend"} == 0
          for: 2m
          labels:
            severity: critical
            service: backend
          annotations:
            summary: "Artisan Platform Backend is down"
            description: "Backend service has been down for more than 2 minutes"
        
        # High error rate
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
          for: 5m
          labels:
            severity: critical
            service: backend
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"
        
        # High response time
        - alert: HighResponseTime
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
          for: 10m
          labels:
            severity: warning
            service: backend
          annotations:
            summary: "High response time"
            description: "95th percentile response time is {{ $value }}s"
        
        # Database connectivity
        - alert: DatabaseConnectionFailure
          expr: postgresql_up == 0
          for: 1m
          labels:
            severity: critical
            service: database
          annotations:
            summary: "Database connection failure"
            description: "Cannot connect to PostgreSQL database"
        
        # High memory usage
        - alert: HighMemoryUsage
          expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
          for: 10m
          labels:
            severity: warning
            service: infrastructure
          annotations:
            summary: "High memory usage"
            description: "Memory usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
        
        # Low disk space
        - alert: LowDiskSpace
          expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.9
          for: 5m
          labels:
            severity: critical
            service: infrastructure
          annotations:
            summary: "Low disk space"
            description: "Disk usage is {{ $value | humanizePercentage }} on {{ $labels.instance }}"
        
        # SSL certificate expiry
        - alert: SSLCertificateExpiry
          expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 7
          for: 1h
          labels:
            severity: warning
            service: infrastructure
          annotations:
            summary: "SSL certificate expiring soon"
            description: "SSL certificate for {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"
```

### Step 6: Install Log Aggregation (Loki)

```bash
# Add Grafana Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values loki-values.yaml
```

Create `loki-values.yaml`:

```yaml
loki:
  enabled: true
  persistence:
    enabled: true
    storageClassName: gp2
    size: 20Gi
  
  config:
    auth_enabled: false
    server:
      http_listen_port: 3100
    
    ingester:
      lifecycler:
        address: 127.0.0.1
        ring:
          kvstore:
            store: inmemory
          replication_factor: 1
    
    schema_config:
      configs:
        - from: 2020-10-24
          store: boltdb-shipper
          object_store: filesystem
          schema: v11
          index:
            prefix: index_
            period: 24h
    
    storage_config:
      boltdb_shipper:
        active_index_directory: /loki/boltdb-shipper-active
        cache_location: /loki/boltdb-shipper-cache
        shared_store: filesystem
      filesystem:
        directory: /loki/chunks
    
    limits_config:
      enforce_metric_name: false
      reject_old_samples: true
      reject_old_samples_max_age: 168h

promtail:
  enabled: true
  config:
    server:
      http_listen_port: 3101
    
    positions:
      filename: /tmp/positions.yaml
    
    clients:
      - url: http://loki:3100/loki/api/v1/push
    
    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels:
              - __meta_kubernetes_pod_controller_name
            regex: ([0-9a-z-.]+?)(-[0-9a-f]{8,10})?
            target_label: __tmp_controller_name
          - source_labels:
              - __meta_kubernetes_pod_label_app_kubernetes_io_name
              - __meta_kubernetes_pod_label_app
              - __tmp_controller_name
              - __meta_kubernetes_pod_name
            regex: ^;*([^;]+)(;.*)?$
            target_label: app
            replacement: $1
          - source_labels:
              - __meta_kubernetes_pod_label_app_kubernetes_io_component
              - __meta_kubernetes_pod_label_component
            regex: ^;*([^;]+)(;.*)?$
            target_label: component
            replacement: $1
          - action: replace
            source_labels:
            - __meta_kubernetes_pod_node_name
            target_label: node_name
          - action: replace
            source_labels:
            - __meta_kubernetes_namespace
            target_label: namespace
          - action: replace
            replacement: /var/log/pods/*$1/*.log
            separator: /
            source_labels:
            - __meta_kubernetes_pod_uid
            - __meta_kubernetes_pod_container_name
            target_label: __path__
```

### Step 7: Create Service Monitors

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: artisan-platform-backend
  namespace: monitoring
  labels:
    app: artisan-platform-backend
spec:
  selector:
    matchLabels:
      app: artisan-platform-backend
  endpoints:
  - port: http
    path: /monitoring/metrics
    interval: 30s

---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: artisan-platform-frontend
  namespace: monitoring
  labels:
    app: artisan-platform-frontend
spec:
  selector:
    matchLabels:
      app: artisan-platform-frontend
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Step 8: Configure Ingress for Grafana

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - grafana.artisan-platform.com
    secretName: grafana-tls
  rules:
  - host: grafana.artisan-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-grafana
            port:
              number: 80
```

## Grafana Dashboard Configuration

### Import Pre-built Dashboards

1. **Kubernetes Cluster Monitoring**: Dashboard ID 7249
2. **Node Exporter Full**: Dashboard ID 1860
3. **PostgreSQL Database**: Dashboard ID 9628
4. **Redis Dashboard**: Dashboard ID 763
5. **Nginx Ingress Controller**: Dashboard ID 9614

### Custom Application Dashboard

Create a custom dashboard for the Artisan Platform with panels for:

- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])`
- **Response Time**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **Active Users**: `active_users_total`
- **Posts Created**: `rate(posts_created_total[5m])`
- **Platform Connections**: `platform_connections_total`

## Verification Steps

### 1. Check Prometheus Targets

```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 -n monitoring

# Open http://localhost:9090/targets in browser
# Verify all targets are UP
```

### 2. Check Grafana Access

```bash
# Port forward to Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Open http://localhost:3000 in browser
# Login with admin credentials
```

### 3. Test Alerting

```bash
# Trigger a test alert
kubectl scale deployment artisan-platform-backend --replicas=0 -n artisan-platform

# Check AlertManager
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093:9093 -n monitoring

# Restore service
kubectl scale deployment artisan-platform-backend --replicas=3 -n artisan-platform
```

## Maintenance Tasks

### Daily
- Check alert status in Grafana
- Review error logs in Loki
- Verify backup completion

### Weekly
- Review dashboard performance
- Check storage usage for Prometheus/Grafana
- Update alert thresholds if needed

### Monthly
- Review and update alert rules
- Clean up old metrics data
- Update monitoring stack components

## Troubleshooting

### Common Issues

#### Prometheus Not Scraping Targets
```bash
# Check service discovery
kubectl get servicemonitor -n monitoring
kubectl describe servicemonitor artisan-platform-backend -n monitoring

# Check service labels
kubectl get svc artisan-platform-backend -o yaml
```

#### Grafana Dashboard Not Loading
```bash
# Check Grafana logs
kubectl logs deployment/prometheus-grafana -n monitoring

# Check data source connectivity
# Go to Grafana > Configuration > Data Sources > Test
```

#### Alerts Not Firing
```bash
# Check AlertManager configuration
kubectl get secret alertmanager-config -n monitoring -o yaml

# Check alert rules
kubectl get prometheusrule -n monitoring
```

---

**Document Version**: 1.0  
**Last Updated**: $(date)  
**Next Review**: Monthly  
**Owner**: DevOps Team