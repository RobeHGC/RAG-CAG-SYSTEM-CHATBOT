# AI Companion Monitoring Stack

This directory contains the complete monitoring infrastructure for the AI Companion application, providing comprehensive observability through metrics, logs, traces, and alerts.

## Architecture Overview

The monitoring stack consists of the following components:

### Core Monitoring
- **Prometheus**: Metrics collection, storage, and alerting
- **Grafana**: Metrics visualization and dashboards
- **Alertmanager**: Alert routing and notification management

### Logging & Search
- **Elasticsearch**: Log storage and full-text search
- **Kibana**: Log visualization and analysis

### Tracing
- **Jaeger**: Distributed tracing and performance analysis

### System Monitoring
- **Node Exporter**: System-level metrics (CPU, memory, disk, network)
- **cAdvisor**: Container metrics and resource usage
- **Redis Exporter**: Redis-specific metrics
- **PostgreSQL Exporter**: PostgreSQL database metrics

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB of available RAM
- Ports 3000, 5601, 8080, 9090, 9093, 9100, 9121, 9187, 9200, 16686 available

### Starting the Monitoring Stack

```bash
# Make the script executable (first time only)
chmod +x scripts/monitoring.sh

# Start all monitoring services
./scripts/monitoring.sh start
```

### Accessing Services

Once started, the following services will be available:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Grafana | http://localhost:3000 | admin / ai-companion-grafana |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Kibana | http://localhost:5601 | - |
| Elasticsearch | http://localhost:9200 | - |
| Jaeger | http://localhost:16686 | - |
| cAdvisor | http://localhost:8080 | - |

## Configuration

### Prometheus Configuration
- **File**: `monitoring/prometheus/prometheus.yml`
- **Purpose**: Defines scrape targets, intervals, and alerting rules
- **Key Sections**:
  - `scrape_configs`: Defines which services to monitor
  - `rule_files`: References alert rule files
  - `alerting`: Configures Alertmanager integration

### Alert Rules
- **File**: `monitoring/prometheus/alert_rules.yml`
- **Purpose**: Defines alerting conditions and thresholds
- **Alert Categories**:
  - Application performance alerts
  - System resource alerts
  - Database health alerts
  - Container monitoring alerts

### Alertmanager Configuration
- **File**: `monitoring/alertmanager/alertmanager.yml`
- **Purpose**: Configures alert routing and notifications
- **Features**:
  - Email notifications
  - Slack integration
  - Alert grouping and inhibition
  - Team-specific routing

### Grafana Dashboards

#### AI Companion Overview Dashboard
- **File**: `monitoring/grafana/dashboards/ai-companion-overview.json`
- **Metrics**:
  - Application status and health
  - Request rate and response times
  - Error rates and performance
  - Memory and CPU usage
  - Database connection pools
  - Cache hit rates
  - LLM request metrics

#### System Metrics Dashboard
- **File**: `monitoring/grafana/dashboards/system-metrics.json`
- **Metrics**:
  - System CPU, memory, and disk usage
  - Network and disk I/O
  - Load averages
  - Container resource usage
  - Redis and PostgreSQL metrics

## Management Commands

The `scripts/monitoring.sh` script provides comprehensive management:

```bash
# Start the monitoring stack
./scripts/monitoring.sh start

# Stop the monitoring stack
./scripts/monitoring.sh stop

# Restart all services
./scripts/monitoring.sh restart

# Check service status
./scripts/monitoring.sh status

# View logs for all services
./scripts/monitoring.sh logs

# View logs for specific service
./scripts/monitoring.sh logs prometheus

# Check health of all services
./scripts/monitoring.sh health

# Update to latest images
./scripts/monitoring.sh update

# Create backup of monitoring data
./scripts/monitoring.sh backup

# Clean up all containers and volumes
./scripts/monitoring.sh cleanup
```

## Application Integration

### Metrics Exposure
The AI Companion application exposes metrics at:
- `http://localhost:8000/metrics` - Main application metrics
- `http://localhost:8000/health` - Health check endpoint

### Required Application Configuration

Ensure your application includes the monitoring components:

```python
# In your main application
from src.common.monitoring import monitor
from src.common.enhanced_logging import setup_logging_for_service
from src.common.sentry_config import sentry_config
from src.common.alerts import alert_manager
from src.common.health_checks import health_manager

# Initialize monitoring
monitor.start_prometheus_server(port=8000, path='/metrics')
setup_logging_for_service('ai-companion', enable_elasticsearch=True)
sentry_config.initialize()
```

### Custom Metrics

Add custom metrics to your application:

```python
from src.common.monitoring import monitor

# Record custom metrics
monitor.record_custom_metric('custom_operation_duration', duration)
monitor.increment_counter('custom_events_total', labels={'event_type': 'user_action'})
```

## Alerting Setup

### Email Configuration
Edit `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'your-smtp-server:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_auth_username: 'your-email@your-domain.com'
  smtp_auth_password: 'your-email-password'
```

### Slack Integration
1. Create a Slack webhook URL
2. Update the webhook URL in `monitoring/alertmanager/alertmanager.yml`
3. Configure channels and routing rules

### Custom Alert Rules
Add custom alerts to `monitoring/prometheus/alert_rules.yml`:

```yaml
- alert: CustomAlert
  expr: your_metric > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Custom alert description"
    description: "Detailed alert information"
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check if required ports are available
   - Ensure sufficient memory (4GB+ recommended)
   - Check Docker daemon status

2. **No metrics showing in Grafana**
   - Verify Prometheus is scraping targets successfully
   - Check application metrics endpoint is accessible
   - Ensure datasource configuration is correct

3. **Alerts not firing**
   - Verify alert rules syntax in Prometheus
   - Check Alertmanager configuration
   - Ensure notification channels are properly configured

### Log Analysis
```bash
# Check specific service logs
./scripts/monitoring.sh logs prometheus
./scripts/monitoring.sh logs grafana
./scripts/monitoring.sh logs alertmanager

# Check service health
./scripts/monitoring.sh health
```

### Performance Tuning

For production environments:

1. **Prometheus**:
   - Adjust retention period in `docker-compose.monitoring.yml`
   - Configure external storage for long-term retention

2. **Elasticsearch**:
   - Increase heap size for larger log volumes
   - Configure index lifecycle management

3. **Grafana**:
   - Enable database backend for dashboard persistence
   - Configure LDAP/OAuth for authentication

## Backup and Recovery

### Creating Backups
```bash
# Create full backup
./scripts/monitoring.sh backup
```

### Restoring from Backup
1. Stop monitoring stack: `./scripts/monitoring.sh stop`
2. Restore data volumes from backup
3. Start monitoring stack: `./scripts/monitoring.sh start`

## Security Considerations

1. **Network Security**:
   - Configure firewall rules for monitoring ports
   - Use reverse proxy for external access
   - Enable TLS for production deployments

2. **Authentication**:
   - Change default Grafana credentials
   - Configure authentication providers
   - Implement access controls

3. **Data Protection**:
   - Regularly backup monitoring data
   - Configure retention policies
   - Sanitize sensitive data in logs

## Support

For monitoring-related issues:
1. Check the troubleshooting section above
2. Review service logs using the monitoring script
3. Consult individual component documentation
4. File issues with specific component details and logs