"""
Comprehensive alerting system for AI Companion monitoring.
Provides configurable alert rules, notifications, and incident tracking.
"""

import asyncio
import json
import logging
import smtplib
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from collections import defaultdict

import httpx
from prometheus_client import CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families

from .monitoring import monitor

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    
    name: str
    description: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "ne"
    duration_seconds: int
    severity: AlertSeverity
    labels: Dict[str, str] = None
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes default
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """Active alert instance."""
    
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime
    resolved_timestamp: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}
    
    @property
    def duration(self) -> timedelta:
        """Get alert duration."""
        end_time = self.resolved_timestamp or datetime.now()
        return end_time - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_timestamp:
            data['resolved_timestamp'] = self.resolved_timestamp.isoformat()
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        return data


class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
    
    async def send_notification(self, alert: Alert) -> bool:
        """
        Send notification for an alert.
        
        Args:
            alert: Alert to send notification for
            
        Returns:
            True if notification sent successfully
        """
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(self, name: str, smtp_host: str, smtp_port: int,
                 username: str, password: str, from_email: str,
                 to_emails: List[str], enabled: bool = True):
        super().__init__(name, enabled)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send email notification."""
        if not self.enabled:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] AI Companion Alert: {alert.rule_name}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert: {alert.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body."""
        severity_color = {
            AlertSeverity.LOW: "#FFA500",
            AlertSeverity.MEDIUM: "#FF6347",
            AlertSeverity.HIGH: "#FF4500",
            AlertSeverity.CRITICAL: "#DC143C"
        }
        
        color = severity_color.get(alert.severity, "#000000")
        
        return f"""
        <html>
        <body>
            <h2 style="color: {color};">[{alert.severity.value.upper()}] AI Companion Alert</h2>
            
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><td><strong>Alert Rule</strong></td><td>{alert.rule_name}</td></tr>
                <tr><td><strong>Status</strong></td><td>{alert.status.value}</td></tr>
                <tr><td><strong>Message</strong></td><td>{alert.message}</td></tr>
                <tr><td><strong>Current Value</strong></td><td>{alert.metric_value}</td></tr>
                <tr><td><strong>Threshold</strong></td><td>{alert.threshold}</td></tr>
                <tr><td><strong>Timestamp</strong></td><td>{alert.timestamp.isoformat()}</td></tr>
                <tr><td><strong>Duration</strong></td><td>{alert.duration}</td></tr>
            </table>
            
            <h3>Labels</h3>
            <ul>
                {chr(10).join([f"<li><strong>{k}:</strong> {v}</li>" for k, v in alert.labels.items()])}
            </ul>
            
            <p>Please investigate this alert and take appropriate action.</p>
            <p><em>This is an automated message from AI Companion monitoring system.</em></p>
        </body>
        </html>
        """


class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel."""
    
    def __init__(self, name: str, webhook_url: str, channel: str = None, 
                 username: str = "AI Companion Monitor", enabled: bool = True):
        super().__init__(name, enabled)
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
    
    async def send_notification(self, alert: Alert) -> bool:
        """Send Slack notification."""
        if not self.enabled:
            return False
        
        try:
            # Create Slack message
            message = self._create_slack_message(alert)
            
            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0
                )
                response.raise_for_status()
            
            logger.info(f"Slack notification sent for alert: {alert.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def _create_slack_message(self, alert: Alert) -> Dict[str, Any]:
        """Create Slack message payload."""
        color_map = {
            AlertSeverity.LOW: "#FFA500",
            AlertSeverity.MEDIUM: "#FF6347", 
            AlertSeverity.HIGH: "#FF4500",
            AlertSeverity.CRITICAL: "#DC143C"
        }
        
        emoji_map = {
            AlertSeverity.LOW: ":warning:",
            AlertSeverity.MEDIUM: ":exclamation:",
            AlertSeverity.HIGH: ":rotating_light:",
            AlertSeverity.CRITICAL: ":fire:"
        }
        
        message = {
            "username": self.username,
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#000000"),
                    "title": f"{emoji_map.get(alert.severity, '')} [{alert.severity.value.upper()}] {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Status",
                            "value": alert.status.value,
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.metric_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True
                        },
                        {
                            "title": "Duration",
                            "value": str(alert.duration),
                            "short": True
                        }
                    ],
                    "timestamp": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        if self.channel:
            message["channel"] = self.channel
        
        return message


class AlertManager:
    """Main alert management system."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels: List[NotificationChannel] = []
        self.rule_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # MTTD/MTTR tracking
        self.incident_metrics = {
            'mttd_samples': [],
            'mttr_samples': [],
            'total_incidents': 0,
            'false_positives': 0
        }
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up default alert rules based on issue requirements."""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                description="Error rate exceeds 5% in 5 minutes",
                metric_name="app_errors_total",
                threshold=0.05,
                comparison="gt",
                duration_seconds=300,
                severity=AlertSeverity.CRITICAL,
                labels={"team": "platform", "component": "application"}
            ),
            AlertRule(
                name="high_response_time",
                description="Average response time exceeds 30 seconds",
                metric_name="app_request_duration_seconds",
                threshold=30.0,
                comparison="gt",
                duration_seconds=600,
                severity=AlertSeverity.HIGH,
                labels={"team": "platform", "component": "application"}
            ),
            AlertRule(
                name="high_memory_usage",
                description="Memory usage exceeds 80% for 10 minutes",
                metric_name="app_memory_usage_bytes",
                threshold=0.8,
                comparison="gt",
                duration_seconds=600,
                severity=AlertSeverity.HIGH,
                labels={"team": "platform", "component": "system"}
            ),
            AlertRule(
                name="database_pool_exhaustion",
                description="Database connection pool utilization > 90%",
                metric_name="db_connections_active",
                threshold=0.9,
                comparison="gt",
                duration_seconds=300,
                severity=AlertSeverity.CRITICAL,
                labels={"team": "platform", "component": "database"}
            ),
            AlertRule(
                name="low_cache_hit_rate",
                description="Cache hit rate below 70% for 15 minutes",
                metric_name="cache_hit_rate",
                threshold=0.7,
                comparison="lt",
                duration_seconds=900,
                severity=AlertSeverity.MEDIUM,
                labels={"team": "platform", "component": "cache"}
            ),
            AlertRule(
                name="memory_consolidation_backlog",
                description="Memory consolidation backlog > 1000 items",
                metric_name="memory_consolidation_backlog",
                threshold=1000,
                comparison="gt",
                duration_seconds=1800,
                severity=AlertSeverity.MEDIUM,
                labels={"team": "ai", "component": "memory"}
            ),
            AlertRule(
                name="llm_timeout_rate",
                description="LLM request timeout rate > 10%",
                metric_name="llm_timeout_rate",
                threshold=0.1,
                comparison="gt",
                duration_seconds=600,
                severity=AlertSeverity.HIGH,
                labels={"team": "ai", "component": "llm"}
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            if rule_name in self.active_alerts:
                self.resolve_alert(rule_name)
            logger.info(f"Removed alert rule: {rule_name}")
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel."""
        self.notification_channels.append(channel)
        logger.info(f"Added notification channel: {channel.name}")
    
    def get_metric_value(self, metric_name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """
        Get current metric value from Prometheus.
        
        Args:
            metric_name: Name of the metric
            labels: Optional label filters
            
        Returns:
            Current metric value or None
        """
        try:
            # Get metrics from the global monitor
            metrics_data = monitor.get_metrics()
            
            # Parse Prometheus metrics
            for family in text_string_to_metric_families(metrics_data):
                if family.name == metric_name:
                    for sample in family.samples:
                        # Check if labels match (simplified implementation)
                        if not labels or all(
                            sample.labels.get(k) == v for k, v in labels.items()
                        ):
                            return sample.value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get metric value for {metric_name}: {e}")
            return None
    
    def evaluate_rule(self, rule: AlertRule) -> bool:
        """
        Evaluate an alert rule.
        
        Args:
            rule: Alert rule to evaluate
            
        Returns:
            True if rule condition is met
        """
        if not rule.enabled:
            return False
        
        metric_value = self.get_metric_value(rule.metric_name, rule.labels)
        if metric_value is None:
            return False
        
        # Store current value for state tracking
        current_time = time.time()
        if rule.name not in self.rule_states:
            self.rule_states[rule.name] = {
                'first_triggered': None,
                'last_value': None,
                'last_notification': 0
            }
        
        state = self.rule_states[rule.name]
        state['last_value'] = metric_value
        
        # Evaluate condition
        condition_met = False
        if rule.comparison == "gt":
            condition_met = metric_value > rule.threshold
        elif rule.comparison == "lt":
            condition_met = metric_value < rule.threshold
        elif rule.comparison == "eq":
            condition_met = metric_value == rule.threshold
        elif rule.comparison == "ne":
            condition_met = metric_value != rule.threshold
        
        if condition_met:
            if state['first_triggered'] is None:
                state['first_triggered'] = current_time
            
            # Check if duration threshold is met
            if current_time - state['first_triggered'] >= rule.duration_seconds:
                return True
        else:
            # Reset state if condition is no longer met
            state['first_triggered'] = None
        
        return False
    
    async def fire_alert(self, rule: AlertRule, metric_value: float):
        """
        Fire an alert for a rule.
        
        Args:
            rule: Alert rule that triggered
            metric_value: Current metric value
        """
        # Check cooldown
        state = self.rule_states[rule.name]
        current_time = time.time()
        
        if current_time - state.get('last_notification', 0) < rule.cooldown_seconds:
            return
        
        # Create alert
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=f"{rule.description}. Current value: {metric_value}, Threshold: {rule.threshold}",
            metric_value=metric_value,
            threshold=rule.threshold,
            timestamp=datetime.now(),
            labels=rule.labels.copy(),
            annotations={
                "description": rule.description,
                "runbook": f"https://docs.ai-companion.com/runbooks/{rule.name}",
                "dashboard": f"https://grafana.ai-companion.com/d/{rule.name}"
            }
        )
        
        # Add to active alerts
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        
        # Record MTTD (time from issue start to detection)
        mttd = current_time - state['first_triggered']
        self.incident_metrics['mttd_samples'].append(mttd)
        self.incident_metrics['total_incidents'] += 1
        
        # Send notifications
        await self._send_notifications(alert)
        
        # Update state
        state['last_notification'] = current_time
        
        logger.warning(f"Alert fired: {rule.name} - {alert.message}")
    
    async def resolve_alert(self, rule_name: str):
        """
        Resolve an active alert.
        
        Args:
            rule_name: Name of the rule to resolve
        """
        if rule_name not in self.active_alerts:
            return
        
        alert = self.active_alerts[rule_name]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_timestamp = datetime.now()
        
        # Record MTTR (time from detection to resolution)
        mttr = (alert.resolved_timestamp - alert.timestamp).total_seconds()
        self.incident_metrics['mttr_samples'].append(mttr)
        
        # Send resolution notification
        await self._send_notifications(alert)
        
        # Remove from active alerts
        del self.active_alerts[rule_name]
        
        # Reset rule state
        if rule_name in self.rule_states:
            self.rule_states[rule_name]['first_triggered'] = None
        
        logger.info(f"Alert resolved: {rule_name}")
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications through all channels."""
        for channel in self.notification_channels:
            try:
                await channel.send_notification(alert)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.name}: {e}")
    
    async def evaluate_all_rules(self):
        """Evaluate all alert rules."""
        for rule_name, rule in self.rules.items():
            try:
                should_fire = self.evaluate_rule(rule)
                
                if should_fire and rule_name not in self.active_alerts:
                    metric_value = self.rule_states[rule_name]['last_value']
                    await self.fire_alert(rule, metric_value)
                elif not should_fire and rule_name in self.active_alerts:
                    await self.resolve_alert(rule_name)
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status summary."""
        active_by_severity = defaultdict(int)
        for alert in self.active_alerts.values():
            active_by_severity[alert.severity.value] += 1
        
        # Calculate MTTD and MTTR
        avg_mttd = sum(self.incident_metrics['mttd_samples']) / len(self.incident_metrics['mttd_samples']) if self.incident_metrics['mttd_samples'] else 0
        avg_mttr = sum(self.incident_metrics['mttr_samples']) / len(self.incident_metrics['mttr_samples']) if self.incident_metrics['mttr_samples'] else 0
        
        return {
            "active_alerts": len(self.active_alerts),
            "active_by_severity": dict(active_by_severity),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "incident_metrics": {
                "avg_mttd_seconds": avg_mttd,
                "avg_mttr_seconds": avg_mttr,
                "total_incidents": self.incident_metrics['total_incidents'],
                "false_positives": self.incident_metrics['false_positives']
            },
            "alert_history_size": len(self.alert_history)
        }
    
    def acknowledge_alert(self, rule_name: str, acknowledged_by: str):
        """Acknowledge an active alert."""
        if rule_name in self.active_alerts:
            self.active_alerts[rule_name].status = AlertStatus.ACKNOWLEDGED
            self.active_alerts[rule_name].acknowledged_by = acknowledged_by
            logger.info(f"Alert acknowledged: {rule_name} by {acknowledged_by}")
    
    def silence_alert(self, rule_name: str, duration_seconds: int = 3600):
        """Silence an alert for a specified duration."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            # You could add logic here to re-enable after duration
            logger.info(f"Alert silenced: {rule_name} for {duration_seconds} seconds")


class AlertScheduler:
    """Scheduler for running alert evaluations."""
    
    def __init__(self, alert_manager: AlertManager, check_interval: int = 60):
        """
        Initialize alert scheduler.
        
        Args:
            alert_manager: AlertManager instance
            check_interval: Check interval in seconds
        """
        self.alert_manager = alert_manager
        self.check_interval = check_interval
        self.running = False
    
    async def start(self):
        """Start the alert evaluation loop."""
        self.running = True
        logger.info("Alert scheduler started")
        
        while self.running:
            try:
                await self.alert_manager.evaluate_all_rules()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the alert evaluation loop."""
        self.running = False
        logger.info("Alert scheduler stopped")


# Global alert manager instance
alert_manager = AlertManager()
alert_scheduler = AlertScheduler(alert_manager)