from rest_framework import serializers
from .models import (
    ServiceEndpoint, HealthCheck, SystemMetrics, 
    APIRequestLog, StatusPageIncident, StatusPageSettings
)


class ServiceEndpointSerializer(serializers.ModelSerializer):
    """Serializer for ServiceEndpoint model"""
    
    status_color = serializers.ReadOnlyField(source='get_status_color')
    uptime_24h = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceEndpoint
        fields = [
            'id', 'name', 'description', 'url_path', 'method',
            'current_status', 'status_color', 'last_check',
            'last_response_time', 'uptime_percentage', 'uptime_24h',
            'is_active', 'check_interval_minutes', 'timeout_seconds',
            'expected_status_code', 'created_at', 'updated_at'
        ]
    
    def get_uptime_24h(self, obj):
        """Get 24-hour uptime percentage"""
        return obj.calculate_uptime(24)


class HealthCheckSerializer(serializers.ModelSerializer):
    """Serializer for HealthCheck model"""
    
    endpoint_name = serializers.ReadOnlyField(source='endpoint.name')
    
    class Meta:
        model = HealthCheck
        fields = [
            'id', 'endpoint', 'endpoint_name', 'timestamp',
            'is_healthy', 'response_time', 'status_code',
            'error_message', 'response_size', 'headers'
        ]


class SystemMetricsSerializer(serializers.ModelSerializer):
    """Serializer for SystemMetrics model"""
    
    class Meta:
        model = SystemMetrics
        fields = [
            'id', 'timestamp', 'db_connection_time', 'db_query_count',
            'memory_usage_mb', 'memory_usage_percent', 'cpu_usage_percent',
            'disk_usage_percent', 'total_requests', 'failed_requests',
            'avg_response_time', 'twilio_status', 'africastalking_status',
            'email_service_status'
        ]


class APIRequestLogSerializer(serializers.ModelSerializer):
    """Serializer for APIRequestLog model"""
    
    user_email = serializers.ReadOnlyField(source='user.email')
    is_error = serializers.ReadOnlyField()
    is_slow = serializers.ReadOnlyField()
    
    class Meta:
        model = APIRequestLog
        fields = [
            'id', 'timestamp', 'method', 'path', 'user', 'user_email',
            'ip_address', 'user_agent', 'status_code', 'response_time',
            'response_size', 'query_params', 'errors', 'is_error', 'is_slow'
        ]


class StatusPageIncidentSerializer(serializers.ModelSerializer):
    """Serializer for StatusPageIncident model"""
    
    affected_endpoints = ServiceEndpointSerializer(many=True, read_only=True)
    severity_color = serializers.ReadOnlyField(source='get_severity_color')
    duration = serializers.ReadOnlyField()
    created_by_name = serializers.ReadOnlyField(source='created_by.full_name')
    
    class Meta:
        model = StatusPageIncident
        fields = [
            'id', 'title', 'description', 'incident_type', 'severity',
            'severity_color', 'status', 'affected_endpoints', 'created_at',
            'started_at', 'resolved_at', 'duration', 'created_by',
            'created_by_name', 'is_public'
        ]


class StatusPageSettingsSerializer(serializers.ModelSerializer):
    """Serializer for StatusPageSettings model"""
    
    class Meta:
        model = StatusPageSettings
        fields = [
            'page_title', 'page_description', 'company_name', 'logo_url',
            'show_response_times', 'show_uptime_percentage', 'show_incident_history',
            'refresh_interval_seconds', 'enable_email_notifications',
            'notification_email', 'primary_color', 'success_color',
            'warning_color', 'danger_color'
        ]


class HealthOverviewSerializer(serializers.Serializer):
    """Serializer for health overview data"""
    
    overall_status = serializers.CharField()
    total_endpoints = serializers.IntegerField()
    operational_endpoints = serializers.IntegerField()
    degraded_endpoints = serializers.IntegerField()
    outage_endpoints = serializers.IntegerField()
    maintenance_endpoints = serializers.IntegerField()
    recent_incidents = StatusPageIncidentSerializer(many=True)
    system_metrics = serializers.DictField()


class EndpointMetricsSerializer(serializers.Serializer):
    """Serializer for endpoint metrics data"""
    
    uptime_percentage = serializers.FloatField()
    avg_response_time = serializers.FloatField()
    total_checks = serializers.IntegerField()
    successful_checks = serializers.IntegerField()
    failed_checks = serializers.IntegerField()
    last_check = serializers.DateTimeField()
    status = serializers.CharField()