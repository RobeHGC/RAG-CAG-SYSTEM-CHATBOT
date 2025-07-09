# deployment_guide.md - Guía de Despliegue en Producción

## 📋 Tabla de Contenidos
1. [Arquitectura de Producción](#arquitectura-de-producción)
2. [Infraestructura Recomendada](#infraestructura-recomendada)
3. [Configuración de Seguridad](#configuración-de-seguridad)
4. [Despliegue con Kubernetes](#despliegue-con-kubernetes)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoreo y Alertas](#monitoreo-y-alertas)
7. [Backup y Recuperación](#backup-y-recuperación)
8. [Escalamiento](#escalamiento)
9. [Checklist de Producción](#checklist-de-producción)

## 🏗️ Arquitectura de Producción

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                             │
│                     (Cloudflare/AWS ALB)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼──────┐           ┌───────▼──────┐
│   Nginx      │           │   Nginx      │
│  (Primary)   │           │ (Secondary)  │
└───────┬──────┘           └───────┬──────┘
        │                           │
        └─────────────┬─────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼───┐       ┌────▼────┐      ┌────▼────┐
│Userbot│       │Supervisor│      │Dashboard│
│  (3x) │       │   (3x)   │      │  (2x)   │
└───┬───┘       └────┬────┘      └────┬────┘
    │                │                 │
    └────────────────┼─────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐          ┌──────▼───────┐
│Redis Cluster │          │Neo4j Cluster │
│  (Primary +  │          │  (3 nodes)   │
│  2 Replicas) │          │              │
└──────────────┘          └──────────────┘
```

## 🖥️ Infraestructura Recomendada

### Opción A: AWS (Recomendada)

```yaml
# terraform/aws/main.tf
resource "aws_instance" "app_servers" {
  count         = 3
  instance_type = "t3.xlarge"  # 4 vCPUs, 16 GB RAM
  ami           = "ami-0c55b159cbfafe1f0"  # Ubuntu 22.04
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 100
    iops        = 3000
  }
  
  tags = {
    Name = "ai-companion-app-${count.index}"
    Type = "application"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "ai-companion-redis"
  replication_group_description = "Redis cluster for AI Companion"
  node_type                  = "cache.r6g.xlarge"
  number_cache_clusters      = 3
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  parameter_group_name = "default.redis7.cluster.on"
  port                = 6379
}

resource "aws_db_instance" "neo4j" {
  # Neo4j en EC2 con EBS optimizado
  # (Neo4j no está disponible en RDS)
}
```

### Opción B: Google Cloud Platform

```yaml
# terraform/gcp/main.tf
resource "google_compute_instance" "app_servers" {
  count        = 3
  name         = "ai-companion-app-${count.index}"
  machine_type = "n2-standard-4"  # 4 vCPUs, 16 GB RAM
  zone         = "us-central1-a"
  
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
      type  = "pd-ssd"
    }
  }
  
  network_interface {
    network = "default"
    access_config {}
  }
}

resource "google_redis_instance" "redis" {
  name               = "ai-companion-redis"
  tier               = "STANDARD_HA"
  memory_size_gb     = 16
  redis_version      = "REDIS_7_0"
  auth_enabled       = true
  replica_count      = 2
}
```

### Opción C: On-Premise / VPS

**Requisitos mínimos por servidor:**
- CPU: 8 cores
- RAM: 32 GB
- Storage: 500 GB NVMe SSD
- Network: 1 Gbps
- OS: Ubuntu 22.04 LTS

## 🔒 Configuración de Seguridad

### 1. Secrets Management

```yaml
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai-companion-secrets
type: Opaque
stringData:
  telegram-token: "encrypted:AQICAHh..."  # Usar AWS KMS o similar
  gemini-api-key: "encrypted:AQICAHh..."
  neo4j-password: "encrypted:AQICAHh..."
  redis-password: "encrypted:AQICAHh..."
  dashboard-secret: "encrypted:AQICAHh..."
```

### 2. Configuración de Firewall

```bash
# scripts/setup_firewall.sh
#!/bin/bash

# Permitir solo tráfico necesario
ufw default deny incoming
ufw default allow outgoing

# SSH (restringir a IPs conocidas)
ufw allow from 203.0.113.0/24 to any port 22

# HTTP/HTTPS (público)
ufw allow 80/tcp
ufw allow 443/tcp

# Redis (solo interno)
ufw allow from 10.0.0.0/8 to any port 6379

# Neo4j (solo interno)
ufw allow from 10.0.0.0/8 to any port 7687

# Dashboard (solo VPN)
ufw allow from 10.8.0.0/16 to any port 3000

ufw enable
```

### 3. SSL/TLS con Let's Encrypt

```nginx
# nginx/sites-available/ai-companion
server {
    listen 443 ssl http2;
    server_name companion.tudominio.com;
    
    ssl_certificate /etc/letsencrypt/live/companion.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/companion.tudominio.com/privkey.pem;
    
    # Configuración SSL moderna
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location /webhook {
        proxy_pass http://supervisor:8080;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /dashboard {
        # Solo accesible via VPN
        allow 10.8.0.0/16;
        deny all;
        
        proxy_pass http://dashboard:3000;
    }
}
```

### 4. Hardening del Sistema

```bash
# scripts/system_hardening.sh
#!/bin/bash

# Deshabilitar servicios innecesarios
systemctl disable bluetooth
systemctl disable cups

# Configurar sysctl para seguridad
cat >> /etc/sysctl.conf << EOF
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_broadcasts = 1
EOF

sysctl -p

# Configurar fail2ban
apt-get install -y fail2ban
systemctl enable fail2ban
```

## 🚀 Despliegue con Kubernetes

### 1. Estructura de Archivos

```
kubernetes/
├── namespace.yaml
├── configmaps/
│   ├── app-config.yaml
│   └── prompts-config.yaml
├── secrets/
│   └── credentials.yaml
├── deployments/
│   ├── userbot.yaml
│   ├── supervisor.yaml
│   └── dashboard.yaml
├── services/
│   ├── internal-services.yaml
│   └── external-services.yaml
├── storage/
│   ├── redis-pvc.yaml
│   └── neo4j-pvc.yaml
└── monitoring/
    ├── prometheus.yaml
    └── grafana.yaml
```

### 2. Deployment del Supervisor

```yaml
# kubernetes/deployments/supervisor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: supervisor
  namespace: ai-companion
spec:
  replicas: 3
  selector:
    matchLabels:
      app: supervisor
  template:
    metadata:
      labels:
        app: supervisor
    spec:
      containers:
      - name: supervisor
        image: gcr.io/project-id/ai-companion-supervisor:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: ai-companion-secrets
              key: redis-url
        - name: NEO4J_URI
          valueFrom:
            secretKeyRef:
              name: ai-companion-secrets
              key: neo4j-uri
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-companion-secrets
              key: gemini-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: prompts
          mountPath: /app/prompts
          readOnly: true
      volumes:
      - name: prompts
        configMap:
          name: prompts-config
```

### 3. Horizontal Pod Autoscaler

```yaml
# kubernetes/hpa/supervisor-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: supervisor-hpa
  namespace: ai-companion
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: supervisor
  minReplicas: 3
  maxReplicas: 10
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
        name: message_queue_depth
      target:
        type: AverageValue
        averageValue: "30"
```

## 🔄 CI/CD Pipeline

### 1. GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  GKE_CLUSTER: ai-companion-prod
  GKE_ZONE: us-central1-a
  DEPLOYMENT_NAME: ai-companion

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Run security scan
      run: |
        pip install bandit safety
        bandit -r app/
        safety check
    
    - name: SonarCloud Scan
      uses: SonarSource/sonarcloud-github-action@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Google Cloud
      uses: google-github-actions/setup-gcloud@v0
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Configure Docker
      run: gcloud auth configure-docker
    
    - name: Build and Push Images
      run: |
        docker build -t gcr.io/$PROJECT_ID/supervisor:$GITHUB_SHA -f docker/Dockerfile.supervisor .
        docker build -t gcr.io/$PROJECT_ID/userbot:$GITHUB_SHA -f docker/Dockerfile.userbot .
        docker build -t gcr.io/$PROJECT_ID/dashboard:$GITHUB_SHA -f docker/Dockerfile.dashboard .
        
        docker push gcr.io/$PROJECT_ID/supervisor:$GITHUB_SHA
        docker push gcr.io/$PROJECT_ID/userbot:$GITHUB_SHA
        docker push gcr.io/$PROJECT_ID/dashboard:$GITHUB_SHA

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Kustomize
      uses: imranismail/setup-kustomize@v1
    
    - name: Deploy to GKE
      run: |
        gcloud container clusters get-credentials $GKE_CLUSTER --zone $GKE_ZONE
        
        cd kubernetes
        kustomize edit set image supervisor=gcr.io/$PROJECT_ID/supervisor:$GITHUB_SHA
        kustomize edit set image userbot=gcr.io/$PROJECT_ID/userbot:$GITHUB_SHA
        kustomize edit set image dashboard=gcr.io/$PROJECT_ID/dashboard:$GITHUB_SHA
        
        kustomize build . | kubectl apply -f -
        kubectl rollout status deployment/supervisor -n ai-companion
        kubectl rollout status deployment/userbot -n ai-companion
        kubectl rollout status deployment/dashboard -n ai-companion
    
    - name: Run smoke tests
      run: |
        ./scripts/smoke_tests.sh
```

### 2. Rollback Strategy

```bash
# scripts/rollback.sh
#!/bin/bash

NAMESPACE="ai-companion"
DEPLOYMENT=$1
REVISION=$2

if [ -z "$DEPLOYMENT" ] || [ -z "$REVISION" ]; then
    echo "Usage: ./rollback.sh <deployment> <revision>"
    exit 1
fi

echo "Rolling back $DEPLOYMENT to revision $REVISION..."

# Crear backup del estado actual
kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o yaml > backup-$DEPLOYMENT-$(date +%s).yaml

# Ejecutar rollback
kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE --to-revision=$REVISION

# Verificar estado
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE

# Verificar health checks
sleep 30
./scripts/health_check.sh

if [ $? -ne 0 ]; then
    echo "Health check failed after rollback!"
    exit 1
fi

echo "Rollback completed successfully"
```

## 📊 Monitoreo y Alertas

### 1. Stack de Monitoreo

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
      - GF_INSTALL_PLUGINS=redis-datasource,neo4j-datasource
    ports:
      - "3001:3000"

  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"

  node_exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

volumes:
  prometheus_data:
  grafana_data:
```

### 2. Alertas Críticas

```yaml
# prometheus/alerts.yml
groups:
  - name: ai_companion_critical
    rules:
    - alert: HighErrorRate
      expr: rate(app_errors_total[5m]) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }} errors per second"
    
    - alert: MemoryPressure
      expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low memory available"
        description: "Only {{ $value | humanizePercentage }} memory available"
    
    - alert: ResponseTimeHigh
      expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 3
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "P95 response time is high"
        description: "95th percentile response time is {{ $value }}s"
    
    - alert: EmotionalCoherenceLow
      expr: emotional_coherence_score < 0.7
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Emotional coherence score is low"
        description: "Score is {{ $value }}, may indicate issues with memory system"
    
    - alert: CacheHitRateLow
      expr: redis_cache_hit_rate < 0.2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Cache hit rate is low"
        description: "Only {{ $value | humanizePercentage }} cache hits"
```

### 3. Dashboards de Grafana

```json
// grafana/dashboards/ai-companion-overview.json
{
  "dashboard": {
    "title": "AI Companion Overview",
    "panels": [
      {
        "title": "Active Users",
        "targets": [
          {
            "expr": "count(rate(messages_received_total[5m]) > 0)"
          }
        ]
      },
      {
        "title": "Message Processing Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(message_processing_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Emotional State Distribution",
        "targets": [
          {
            "expr": "sum by (emotion) (emotional_state_current)"
          }
        ]
      },
      {
        "title": "Memory Operations",
        "targets": [
          {
            "expr": "rate(memory_operations_total[5m])"
          }
        ]
      }
    ]
  }
}
```

## 💾 Backup y Recuperación

### 1. Estrategia de Backup

```bash
# scripts/backup.sh
#!/bin/bash

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup Redis
echo "Backing up Redis..."
redis-cli --rdb $BACKUP_DIR/redis_dump.rdb

# Backup Neo4j
echo "Backing up Neo4j..."
neo4j-admin dump --database=neo4j --to=$BACKUP_DIR/neo4j_backup.dump

# Backup configuración
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config_backup.tar.gz /app/config /app/prompts

# Backup a S3
echo "Uploading to S3..."
aws s3 sync $BACKUP_DIR s3://ai-companion-backups/$BACKUP_DIR/

# Limpiar backups antiguos (mantener últimos 30 días)
find /backups -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

### 2. Plan de Recuperación

```bash
# scripts/restore.sh
#!/bin/bash

BACKUP_ID=$1

if [ -z "$BACKUP_ID" ]; then
    echo "Usage: ./restore.sh <backup_id>"
    exit 1
fi

# Descargar backup de S3
aws s3 sync s3://ai-companion-backups/$BACKUP_ID /tmp/restore/

# Detener servicios
kubectl scale deployment --all --replicas=0 -n ai-companion

# Restaurar Redis
redis-cli --pipe < /tmp/restore/redis_dump.rdb

# Restaurar Neo4j
systemctl stop neo4j
neo4j-admin load --from=/tmp/restore/neo4j_backup.dump --database=neo4j --force
systemctl start neo4j

# Restaurar configuración
tar -xzf /tmp/restore/config_backup.tar.gz -C /

# Reiniciar servicios
kubectl scale deployment supervisor --replicas=3 -n ai-companion
kubectl scale deployment userbot --replicas=3 -n ai-companion
kubectl scale deployment dashboard --replicas=2 -n ai-companion

# Verificar
./scripts/health_check.sh
```

### 3. Backup Automático

```yaml
# kubernetes/cronjobs/backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-job
  namespace: ai-companion
spec:
  schedule: "0 3 * * *"  # 3 AM diario
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: gcr.io/project-id/backup-tool:latest
            env:
            - name: S3_BUCKET
              value: ai-companion-backups
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: ai-companion-secrets
                  key: redis-url
            - name: NEO4J_URI
              valueFrom:
                secretKeyRef:
                  name: ai-companion-secrets
                  key: neo4j-uri
            command: ["/scripts/backup.sh"]
          restartPolicy: OnFailure
```

## 📈 Escalamiento

### 1. Escalamiento Horizontal

```yaml
# kubernetes/autoscaling/userbot-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: userbot-hpa
  namespace: ai-companion
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: userbot
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Pods
    pods:
      metric:
        name: telegram_messages_per_second
      target:
        type: AverageValue
        averageValue: "50"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### 2. Escalamiento de Base de Datos

```bash
# scripts/scale_databases.sh
#!/bin/bash

# Escalar Redis
echo "Scaling Redis cluster..."
redis-cli --cluster add-node new-node:6379 existing-node:6379
redis-cli --cluster rebalance existing-node:6379

# Escalar Neo4j (agregar read replica)
echo "Adding Neo4j read replica..."
neo4j-admin unbind
neo4j-admin set-initial-password $NEO4J_PASSWORD
neo4j-admin bind --initial-mode=replica --initial-discover=neo4j-core-1:5000
```

### 3. Optimizaciones de Performance

```python
# config/production_optimizations.py

# Cache agresivo
REDIS_CACHE_CONFIG = {
    'default_ttl': 3600,  # 1 hora
    'max_connections': 200,
    'connection_pool_kwargs': {
        'max_connections': 200,
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            1: 1,   # TCP_KEEPIDLE
            2: 2,   # TCP_KEEPINTVL  
            3: 3,   # TCP_KEEPCNT
        }
    }
}

# Batch processing
BATCH_CONFIG = {
    'message_batch_size': 50,
    'memory_consolidation_batch': 100,
    'embedding_batch_size': 64
}

# Connection pooling
NEO4J_POOL_CONFIG = {
    'max_connection_pool_size': 100,
    'connection_acquisition_timeout': 30,
    'max_transaction_retry_time': 30,
    'keep_alive': True
}

# Async processing
CELERY_CONFIG = {
    'worker_prefetch_multiplier': 4,
    'task_acks_late': True,
    'worker_max_tasks_per_child': 1000,
    'worker_disable_rate_limits': True,
    'result_expires': 3600
}
```

## ✅ Checklist de Producción

### Pre-despliegue
- [ ] Todos los tests pasan (unit, integration, e2e)
- [ ] Security scan sin vulnerabilidades críticas
- [ ] Performance testing completado
- [ ] Documentación actualizada
- [ ] Runbook de operaciones creado

### Seguridad
- [ ] Secrets encriptados y en vault seguro
- [ ] SSL/TLS configurado correctamente
- [ ] Firewall rules configuradas
- [ ] Autenticación y autorización implementadas
- [ ] Rate limiting activado
- [ ] CORS configurado correctamente

### Infraestructura
- [ ] Alta disponibilidad configurada
- [ ] Load balancers configurados
- [ ] Auto-scaling configurado
- [ ] Backups automáticos programados
- [ ] Disaster recovery plan probado

### Monitoreo
- [ ] Métricas de aplicación expuestas
- [ ] Dashboards de Grafana configurados
- [ ] Alertas críticas configuradas
- [ ] Logs centralizados
- [ ] Tracing distribuido implementado

### Performance
- [ ] CDN configurado para assets estáticos
- [ ] Compresión activada
- [ ] Cache headers optimizados
- [ ] Database índices optimizados
- [ ] Query optimization completado

### Operaciones
- [ ] CI/CD pipeline funcionando
- [ ] Rollback procedure documentado
- [ ] On-call rotation establecido
- [ ] Incident response plan creado
- [ ] SLAs definidos y monitoreados

## 🚨 Procedimientos de Emergencia

### 1. Alta Carga Inesperada
```bash
# Escalar inmediatamente
kubectl scale deployment userbot --replicas=10 -n ai-companion
kubectl scale deployment supervisor --replicas=8 -n ai-companion

# Activar rate limiting estricto
kubectl set env deployment/userbot RATE_LIMIT_STRICT=true -n ai-companion

# Monitorear
watch kubectl top pods -n ai-companion
```

### 2. Memory Leak Detectado
```bash
# Identificar pods problemáticos
kubectl top pods -n ai-companion --sort-by=memory

# Reiniciar con límites estrictos
kubectl set resources deployment/supervisor --limits=memory=2Gi -n ai-companion
kubectl rollout restart deployment/supervisor -n ai-companion
```

### 3. Database Corruption
```bash
# Cambiar a modo read-only
kubectl set env deployment/supervisor DATABASE_MODE=readonly -n ai-companion

# Iniciar recuperación
./scripts/emergency_recovery.sh

# Verificar integridad
./scripts/verify_data_integrity.sh
```

## 📚 Recursos Adicionales

- [Runbook de Operaciones](./runbook.md)
- [Guía de Troubleshooting](./troubleshooting.md)
- [SLA y Métricas](./sla_metrics.md)
- [Security Best Practices](./security.md)

---

**¡Felicidades!** 🎉 Tu AI Companion está listo para producción.

Para soporte 24/7, contacta al equipo de DevOps en: devops@tuempresa.com