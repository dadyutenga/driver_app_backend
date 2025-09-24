from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import (
    ServiceEndpoint, HealthCheck, SystemMetrics, 
    APIRequestLog, StatusPageIncident, StatusPageSettings
)


@admin.register(ServiceEndpoint)
class ServiceEndpointAdmin(admin.ModelAdmin):
    """Admin for Service Endpoints"""
    
    list_display = [
        'name', 'method', 'url_path', 'current_status_display', 
        'uptime_percentage_display', 'last_response_time_display', 
        'last_check_display', 'is_active'
    ]
    list_filter = ['current_status', 'is_active', 'method', 'created_at']
    search_fields = ['name', 'url_path', 'description']
    readonly_fields = ['current_status', 'last_check', 'last_response_time', 'uptime_percentage']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'url_path', 'method')
        }),
        ('Configuration', {
            'fields': ('is_active', 'check_interval_minutes', 'timeout_seconds', 'expected_status_code')
        }),
        ('Current Status', {
            'fields': ('current_status', 'last_check', 'last_response_time', 'uptime_percentage'),
            'classes': ['collapse']
        }),
    )
    
    def current_status_display(self, obj):
        color = obj.get_status_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_current_status_display()
        )
    current_status_display.short_description = 'Status'
    
    def uptime_percentage_display(self, obj):
        uptime = obj.uptime_percentage
        if uptime >= 99.9:
            color = '#10b981'  # Green
        elif uptime >= 99.0:
            color = '#f59e0b'  # Yellow
        else:
            color = '#ef4444'  # Red
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
            color,
            uptime
        )
    uptime_percentage_display.short_description = 'Uptime (24h)'
    
    def last_response_time_display(self, obj):
        if obj.last_response_time:
            time_ms = obj.last_response_time * 1000
            if time_ms < 500:
                color = '#10b981'  # Green
            elif time_ms < 2000:
                color = '#f59e0b'  # Yellow
            else:
                color = '#ef4444'  # Red
            
            return format_html(
                '<span style="color: {};">{:.0f}ms</span>',
                color,
                time_ms
            )
        return '-'
    last_response_time_display.short_description = 'Last Response Time'
    
    def last_check_display(self, obj):
        if obj.last_check:
            return obj.last_check.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'
    last_check_display.short_description = 'Last Check'
    
    actions = ['run_health_check', 'enable_endpoints', 'disable_endpoints']
    
    def run_health_check(self, request, queryset):
        """Action to run health check on selected endpoints"""
        from .services import health_check_service
        
        count = 0
        for endpoint in queryset:
            health_check_service.check_endpoint(endpoint)
            count += 1
        
        self.message_user(request, f'Health check completed for {count} endpoint(s).')
    run_health_check.short_description = 'Run health check on selected endpoints'
    
    def enable_endpoints(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} endpoint(s) enabled.')
    enable_endpoints.short_description = 'Enable selected endpoints'
    
    def disable_endpoints(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} endpoint(s) disabled.')
    disable_endpoints.short_description = 'Disable selected endpoints'


@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    """Admin for Health Checks"""
    
    list_display = [
        'endpoint', 'timestamp', 'is_healthy_display', 
        'response_time_display', 'status_code', 'error_message_short'
    ]
    list_filter = ['is_healthy', 'timestamp', 'endpoint', 'status_code']
    search_fields = ['endpoint__name', 'error_message']
    readonly_fields = ['timestamp']
    
    def is_healthy_display(self, obj):
        if obj.is_healthy:
            return format_html('<span style="color: #10b981;">✓ Healthy</span>')
        else:
            return format_html('<span style="color: #ef4444;">✗ Unhealthy</span>')
    is_healthy_display.short_description = 'Health Status'
    
    def response_time_display(self, obj):
        time_ms = obj.response_time * 1000
        if time_ms < 500:
            color = '#10b981'  # Green
        elif time_ms < 2000:
            color = '#f59e0b'  # Yellow
        else:
            color = '#ef4444'  # Red
        
        return format_html(
            '<span style="color: {};">{:.0f}ms</span>',
            color,
            time_ms
        )
    response_time_display.short_description = 'Response Time'
    
    def error_message_short(self, obj):
        if obj.error_message:
            return obj.error_message[:50] + ('...' if len(obj.error_message) > 50 else '')
        return '-'
    error_message_short.short_description = 'Error'


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    """Admin for System Metrics"""
    
    list_display = [
        'timestamp', 'cpu_usage_display', 'memory_usage_display',
        'db_connection_time_display', 'requests_summary', 'external_services_status'
    ]
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
    
    def cpu_usage_display(self, obj):
        cpu = obj.cpu_usage_percent or 0
        color = '#10b981' if cpu < 70 else '#f59e0b' if cpu < 90 else '#ef4444'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, cpu)
    cpu_usage_display.short_description = 'CPU Usage'
    
    def memory_usage_display(self, obj):
        memory = obj.memory_usage_percent or 0
        color = '#10b981' if memory < 70 else '#f59e0b' if memory < 90 else '#ef4444'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, memory)
    memory_usage_display.short_description = 'Memory Usage'
    
    def db_connection_time_display(self, obj):
        if obj.db_connection_time:
            time_ms = obj.db_connection_time * 1000
            color = '#10b981' if time_ms < 100 else '#f59e0b' if time_ms < 500 else '#ef4444'
            return format_html('<span style="color: {};">{:.0f}ms</span>', color, time_ms)
        return '-'
    db_connection_time_display.short_description = 'DB Connection Time'
    
    def requests_summary(self, obj):
        total = obj.total_requests
        failed = obj.failed_requests
        error_rate = (failed / total * 100) if total > 0 else 0
        
        color = '#10b981' if error_rate < 1 else '#f59e0b' if error_rate < 5 else '#ef4444'
        return format_html(
            '{} total, <span style="color: {};">{} failed ({:.1f}%)</span>',
            total, color, failed, error_rate
        )
    requests_summary.short_description = 'Requests (1h)'
    
    def external_services_status(self, obj):
        services = []
        if obj.twilio_status:
            color = '#10b981' if obj.twilio_status == 'operational' else '#ef4444'
            services.append(f'<span style="color: {color};">Twilio</span>')
        if obj.africastalking_status:
            color = '#10b981' if obj.africastalking_status == 'operational' else '#ef4444'
            services.append(f'<span style="color: {color};">AT</span>')
        if obj.email_service_status:
            color = '#10b981' if obj.email_service_status == 'operational' else '#ef4444'
            services.append(f'<span style="color: {color};">Email</span>')
        
        return format_html(' | '.join(services)) if services else '-'
    external_services_status.short_description = 'External Services'


@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    """Admin for API Request Logs"""
    
    list_display = [
        'timestamp', 'method', 'path_short', 'status_code_display',
        'response_time_display', 'user', 'ip_address'
    ]
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['path', 'user__email', 'ip_address', 'errors']
    readonly_fields = ['timestamp']
    
    def path_short(self, obj):
        return obj.path[:50] + ('...' if len(obj.path) > 50 else '')
    path_short.short_description = 'Path'
    
    def status_code_display(self, obj):
        if obj.status_code < 300:
            color = '#10b981'  # Green
        elif obj.status_code < 400:
            color = '#f59e0b'  # Yellow
        elif obj.status_code < 500:
            color = '#f97316'  # Orange
        else:
            color = '#ef4444'  # Red
        
        return format_html('<span style="color: {};">{}</span>', color, obj.status_code)
    status_code_display.short_description = 'Status'
    
    def response_time_display(self, obj):
        time_ms = obj.response_time * 1000
        if time_ms < 500:
            color = '#10b981'  # Green
        elif time_ms < 2000:
            color = '#f59e0b'  # Yellow
        else:
            color = '#ef4444'  # Red
        
        return format_html('<span style="color: {};">{:.0f}ms</span>', color, time_ms)
    response_time_display.short_description = 'Response Time'


@admin.register(StatusPageIncident)
class StatusPageIncidentAdmin(admin.ModelAdmin):
    """Admin for Status Page Incidents"""
    
    list_display = [
        'title', 'incident_type', 'severity_display', 'status_display',
        'created_at', 'duration_display', 'is_public'
    ]
    list_filter = ['incident_type', 'severity', 'status', 'is_public', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['affected_endpoints']
    readonly_fields = ['created_at', 'duration']
    
    fieldsets = (
        ('Incident Details', {
            'fields': ('title', 'description', 'incident_type', 'severity', 'status')
        }),
        ('Affected Services', {
            'fields': ('affected_endpoints',)
        }),
        ('Timeline', {
            'fields': ('started_at', 'resolved_at', 'duration'),
            'classes': ['collapse']
        }),
        ('Settings', {
            'fields': ('is_public', 'created_by')
        }),
    )
    
    def severity_display(self, obj):
        color = obj.get_severity_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display()
        )
    severity_display.short_description = 'Severity'
    
    def status_display(self, obj):
        status_colors = {
            'investigating': '#f59e0b',
            'identified': '#f97316',
            'monitoring': '#3b82f6',
            'resolved': '#10b981',
            'scheduled': '#6b7280',
            'in_progress': '#f59e0b',
            'completed': '#10b981',
        }
        color = status_colors.get(obj.status, '#6b7280')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def duration_display(self, obj):
        if obj.duration:
            return str(obj.duration)
        return 'Ongoing' if obj.started_at and not obj.resolved_at else '-'
    duration_display.short_description = 'Duration'


@admin.register(StatusPageSettings)
class StatusPageSettingsAdmin(admin.ModelAdmin):
    """Admin for Status Page Settings"""
    
    fieldsets = (
        ('General Settings', {
            'fields': ('page_title', 'page_description', 'company_name', 'logo_url')
        }),
        ('Display Settings', {
            'fields': ('show_response_times', 'show_uptime_percentage', 
                      'show_incident_history', 'refresh_interval_seconds')
        }),
        ('Notification Settings', {
            'fields': ('enable_email_notifications', 'notification_email')
        }),
        ('Theme Settings', {
            'fields': ('primary_color', 'success_color', 'warning_color', 'danger_color'),
            'classes': ['collapse']
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one settings object
        return not StatusPageSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False