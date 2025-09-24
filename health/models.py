from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

User = get_user_model()


class ServiceEndpoint(models.Model):
    """Model to define service endpoints to monitor"""
    
    STATUS_CHOICES = [
        ('operational', 'Operational'),
        ('degraded', 'Degraded Performance'),
        ('partial_outage', 'Partial Outage'),
        ('major_outage', 'Major Outage'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    url_path = models.CharField(max_length=255, help_text="API endpoint path")
    method = models.CharField(max_length=10, default='GET', choices=[
        ('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), 
        ('DELETE', 'DELETE'), ('PATCH', 'PATCH')
    ])
    
    # Configuration
    is_active = models.BooleanField(default=True)
    check_interval_minutes = models.IntegerField(default=5)
    timeout_seconds = models.IntegerField(default=30)
    expected_status_code = models.IntegerField(default=200)
    
    # Current status
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='operational')
    last_check = models.DateTimeField(null=True, blank=True)
    last_response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    uptime_percentage = models.FloatField(default=100.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'health_service_endpoint'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.method} {self.url_path})"
    
    def get_status_color(self):
        """Get color code for status"""
        colors = {
            'operational': '#10b981',      # Green
            'degraded': '#f59e0b',         # Yellow
            'partial_outage': '#f97316',   # Orange
            'major_outage': '#ef4444',     # Red
            'maintenance': '#6b7280',      # Gray
        }
        return colors.get(self.current_status, '#6b7280')
    
    def calculate_uptime(self, hours=24):
        """Calculate uptime percentage for the last N hours"""
        from datetime import timedelta
        
        since = timezone.now() - timedelta(hours=hours)
        checks = self.health_checks.filter(timestamp__gte=since)
        
        if not checks.exists():
            return 100.0
            
        total_checks = checks.count()
        successful_checks = checks.filter(is_healthy=True).count()
        
        uptime = (successful_checks / total_checks) * 100 if total_checks > 0 else 100.0
        return round(uptime, 2)


class HealthCheck(models.Model):
    """Model to store health check results"""
    
    endpoint = models.ForeignKey(ServiceEndpoint, on_delete=models.CASCADE, related_name='health_checks')
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Check results
    is_healthy = models.BooleanField(default=True)
    response_time = models.FloatField(help_text="Response time in seconds")
    status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Additional metrics
    response_size = models.IntegerField(null=True, blank=True, help_text="Response size in bytes")
    headers = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'health_check_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['endpoint', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['is_healthy']),
        ]
        
    def __str__(self):
        status = "✓" if self.is_healthy else "✗"
        return f"{status} {self.endpoint.name} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class SystemMetrics(models.Model):
    """Model to store system-wide metrics"""
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Database metrics
    db_connection_time = models.FloatField(null=True, blank=True)
    db_query_count = models.IntegerField(default=0)
    
    # Memory metrics
    memory_usage_mb = models.FloatField(null=True, blank=True)
    memory_usage_percent = models.FloatField(null=True, blank=True)
    
    # CPU metrics
    cpu_usage_percent = models.FloatField(null=True, blank=True)
    
    # Disk metrics
    disk_usage_percent = models.FloatField(null=True, blank=True)
    
    # Request metrics
    total_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    avg_response_time = models.FloatField(null=True, blank=True)
    
    # External service status
    twilio_status = models.CharField(max_length=20, default='unknown')
    africastalking_status = models.CharField(max_length=20, default='unknown')
    email_service_status = models.CharField(max_length=20, default='unknown')
    
    class Meta:
        db_table = 'system_metrics'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"System Metrics at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class APIRequestLog(models.Model):
    """Model to log API requests for monitoring"""
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Request details
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Response details
    status_code = models.IntegerField()
    response_time = models.FloatField(help_text="Response time in seconds")
    response_size = models.IntegerField(null=True, blank=True, help_text="Response size in bytes")
    
    # Additional data
    query_params = models.JSONField(default=dict, blank=True)
    errors = models.TextField(blank=True)
    
    class Meta:
        db_table = 'api_request_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['path', '-timestamp']),
            models.Index(fields=['status_code', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
        
    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code} ({self.response_time:.3f}s)"
    
    @property
    def is_error(self):
        return self.status_code >= 400
    
    @property
    def is_slow(self):
        return self.response_time > 2.0  # More than 2 seconds


class StatusPageIncident(models.Model):
    """Model to track incidents and maintenance"""
    
    INCIDENT_TYPES = [
        ('incident', 'Incident'),
        ('maintenance', 'Scheduled Maintenance'),
        ('degradation', 'Performance Degradation'),
    ]
    
    STATUS_CHOICES = [
        ('investigating', 'Investigating'),
        ('identified', 'Identified'),
        ('monitoring', 'Monitoring'),
        ('resolved', 'Resolved'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPES, default='incident')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='investigating')
    
    # Affected services
    affected_endpoints = models.ManyToManyField(ServiceEndpoint, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'status_page_incident'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} ({self.status})"
    
    @property
    def duration(self):
        if self.started_at and self.resolved_at:
            return self.resolved_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    def get_severity_color(self):
        """Get color code for severity"""
        colors = {
            'low': '#10b981',      # Green
            'medium': '#f59e0b',   # Yellow
            'high': '#f97316',     # Orange
            'critical': '#ef4444', # Red
        }
        return colors.get(self.severity, '#6b7280')


class StatusPageSettings(models.Model):
    """Model to store status page configuration"""
    
    # General settings
    page_title = models.CharField(max_length=100, default="Driver App Status")
    page_description = models.TextField(default="Current status of Driver App services")
    company_name = models.CharField(max_length=100, default="Driver App")
    logo_url = models.URLField(blank=True)
    
    # Display settings
    show_response_times = models.BooleanField(default=True)
    show_uptime_percentage = models.BooleanField(default=True)
    show_incident_history = models.BooleanField(default=True)
    refresh_interval_seconds = models.IntegerField(default=60)
    
    # Notification settings
    enable_email_notifications = models.BooleanField(default=True)
    notification_email = models.EmailField(blank=True)
    
    # Theme settings
    primary_color = models.CharField(max_length=7, default="#3b82f6")
    success_color = models.CharField(max_length=7, default="#10b981")
    warning_color = models.CharField(max_length=7, default="#f59e0b")
    danger_color = models.CharField(max_length=7, default="#ef4444")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'status_page_settings'
        verbose_name = 'Status Page Settings'
        verbose_name_plural = 'Status Page Settings'
        
    def __str__(self):
        return f"Status Page Settings for {self.company_name}"
    
    @classmethod
    def get_settings(cls):
        """Get the status page settings (singleton)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings