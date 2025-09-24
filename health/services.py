import requests
import time
import psutil
import logging
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.test.client import Client
from django.db import models
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
import json

from .models import (
    ServiceEndpoint, HealthCheck, SystemMetrics, 
    APIRequestLog, StatusPageIncident
)

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for performing health checks on endpoints"""
    
    def __init__(self):
        self.client = Client()
        self.session = requests.Session()
        self.session.timeout = 30
    
    def check_endpoint(self, endpoint: ServiceEndpoint) -> HealthCheck:
        """Perform health check on a single endpoint"""
        start_time = time.time()
        
        try:
            # Prepare request data
            url = f"http://localhost:8000{endpoint.url_path}"
            headers = {'User-Agent': 'HealthCheck/1.0'}
            
            # Make request based on method
            if endpoint.method == 'GET':
                response = self.session.get(url, headers=headers, timeout=endpoint.timeout_seconds)
            elif endpoint.method == 'POST':
                response = self.session.post(url, headers=headers, timeout=endpoint.timeout_seconds)
            elif endpoint.method == 'PUT':
                response = self.session.put(url, headers=headers, timeout=endpoint.timeout_seconds)
            elif endpoint.method == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=endpoint.timeout_seconds)
            elif endpoint.method == 'PATCH':
                response = self.session.patch(url, headers=headers, timeout=endpoint.timeout_seconds)
            else:
                response = self.session.get(url, headers=headers, timeout=endpoint.timeout_seconds)
            
            response_time = time.time() - start_time
            
            # Determine if healthy
            is_healthy = response.status_code == endpoint.expected_status_code
            
            # Create health check record
            health_check = HealthCheck.objects.create(
                endpoint=endpoint,
                is_healthy=is_healthy,
                response_time=response_time,
                status_code=response.status_code,
                response_size=len(response.content) if response.content else 0,
                headers=dict(response.headers),
                error_message="" if is_healthy else f"Expected {endpoint.expected_status_code}, got {response.status_code}"
            )
            
            # Update endpoint status
            self._update_endpoint_status(endpoint, health_check)
            
            return health_check
            
        except requests.exceptions.Timeout:
            response_time = endpoint.timeout_seconds
            error_message = f"Request timeout after {endpoint.timeout_seconds} seconds"
            
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            error_message = f"Connection error: {str(e)}"
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            error_message = f"Request error: {str(e)}"
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = f"Unexpected error: {str(e)}"
        
        # Create failed health check record
        health_check = HealthCheck.objects.create(
            endpoint=endpoint,
            is_healthy=False,
            response_time=response_time,
            error_message=error_message
        )
        
        # Update endpoint status
        self._update_endpoint_status(endpoint, health_check)
        
        return health_check
    
    def _update_endpoint_status(self, endpoint: ServiceEndpoint, health_check: HealthCheck):
        """Update endpoint current status based on health check"""
        endpoint.last_check = health_check.timestamp
        endpoint.last_response_time = health_check.response_time
        
        # Calculate uptime for last 24 hours
        endpoint.uptime_percentage = endpoint.calculate_uptime(24)
        
        # Determine current status
        if not health_check.is_healthy:
            if endpoint.current_status == 'operational':
                endpoint.current_status = 'degraded'
        else:
            # Check recent health
            recent_checks = endpoint.health_checks.filter(
                timestamp__gte=timezone.now() - timedelta(minutes=15)
            ).order_by('-timestamp')[:5]
            
            if recent_checks.exists():
                healthy_count = sum(1 for check in recent_checks if check.is_healthy)
                health_ratio = healthy_count / len(recent_checks)
                
                if health_ratio >= 0.8:
                    endpoint.current_status = 'operational'
                elif health_ratio >= 0.6:
                    endpoint.current_status = 'degraded'
                elif health_ratio >= 0.3:
                    endpoint.current_status = 'partial_outage'
                else:
                    endpoint.current_status = 'major_outage'
        
        endpoint.save()
    
    def check_all_endpoints(self) -> List[HealthCheck]:
        """Check all active endpoints"""
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        results = []
        
        for endpoint in endpoints:
            try:
                health_check = self.check_endpoint(endpoint)
                results.append(health_check)
                logger.info(f"Health check completed for {endpoint.name}: {'✓' if health_check.is_healthy else '✗'}")
            except Exception as e:
                logger.error(f"Error checking endpoint {endpoint.name}: {e}")
        
        return results
    
    def get_endpoint_metrics(self, endpoint: ServiceEndpoint, hours: int = 24) -> Dict:
        """Get metrics for a specific endpoint"""
        since = timezone.now() - timedelta(hours=hours)
        checks = endpoint.health_checks.filter(timestamp__gte=since)
        
        if not checks.exists():
            return {
                'uptime_percentage': 100.0,
                'avg_response_time': 0.0,
                'total_checks': 0,
                'successful_checks': 0,
                'failed_checks': 0,
                'last_check': None,
                'status': 'operational'
            }
        
        successful_checks = checks.filter(is_healthy=True)
        failed_checks = checks.filter(is_healthy=False)
        
        uptime = (successful_checks.count() / checks.count()) * 100 if checks.count() > 0 else 100.0
        avg_response_time = checks.aggregate(
            avg_time=models.Avg('response_time')
        )['avg_time'] or 0.0
        
        return {
            'uptime_percentage': round(uptime, 2),
            'avg_response_time': round(avg_response_time, 3),
            'total_checks': checks.count(),
            'successful_checks': successful_checks.count(),
            'failed_checks': failed_checks.count(),
            'last_check': checks.first().timestamp if checks.exists() else None,
            'status': endpoint.current_status
        }


class SystemMetricsService:
    """Service for collecting system metrics"""
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # Database metrics
            db_start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_connection_time = time.time() - db_start
            
            # System metrics
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            # Request metrics from recent API logs
            recent_logs = APIRequestLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=1)
            )
            
            total_requests = recent_logs.count()
            failed_requests = recent_logs.filter(status_code__gte=400).count()
            avg_response_time = recent_logs.aggregate(
                avg_time=models.Avg('response_time')
            )['avg_time'] or 0.0
            
            # External service status
            external_services = self._check_external_services()
            
            # Create metrics record
            metrics = SystemMetrics.objects.create(
                db_connection_time=db_connection_time,
                memory_usage_mb=memory.used / (1024 * 1024),
                memory_usage_percent=memory.percent,
                cpu_usage_percent=cpu_percent,
                disk_usage_percent=disk.percent,
                total_requests=total_requests,
                failed_requests=failed_requests,
                avg_response_time=avg_response_time,
                **external_services
            )
            
            logger.info(f"System metrics collected: CPU {cpu_percent}%, Memory {memory.percent}%")
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics.objects.create()
    
    def _check_external_services(self) -> Dict[str, str]:
        """Check status of external services"""
        services = {
            'twilio_status': 'unknown',
            'africastalking_status': 'unknown',
            'email_service_status': 'unknown'
        }
        
        # Check Twilio status
        try:
            if hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
                services['twilio_status'] = 'operational'
        except Exception:
            services['twilio_status'] = 'error'
        
        # Check AfricasTalking status
        try:
            if hasattr(settings, 'AFRICASTALKING_USERNAME'):
                # Simple check - if we can import and initialize
                import africastalking
                services['africastalking_status'] = 'operational'
        except Exception:
            services['africastalking_status'] = 'error'
        
        # Check email service
        try:
            from django.core.mail import get_connection
            connection = get_connection()
            connection.open()
            connection.close()
            services['email_service_status'] = 'operational'
        except Exception:
            services['email_service_status'] = 'error'
        
        return services
    
    def get_system_overview(self, hours: int = 24) -> Dict:
        """Get system overview for the last N hours"""
        since = timezone.now() - timedelta(hours=hours)
        metrics = SystemMetrics.objects.filter(timestamp__gte=since)
        
        if not metrics.exists():
            return {
                'avg_cpu_usage': 0.0,
                'avg_memory_usage': 0.0,
                'avg_response_time': 0.0,
                'total_requests': 0,
                'failed_requests': 0,
                'error_rate': 0.0
            }
        
        # Calculate averages
        avg_cpu = metrics.aggregate(avg=models.Avg('cpu_usage_percent'))['avg'] or 0.0
        avg_memory = metrics.aggregate(avg=models.Avg('memory_usage_percent'))['avg'] or 0.0
        avg_response_time = metrics.aggregate(avg=models.Avg('avg_response_time'))['avg'] or 0.0
        
        # Get totals from latest metric
        latest_metric = metrics.first()
        total_requests = latest_metric.total_requests if latest_metric else 0
        failed_requests = latest_metric.failed_requests if latest_metric else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'avg_cpu_usage': round(avg_cpu, 2),
            'avg_memory_usage': round(avg_memory, 2),
            'avg_response_time': round(avg_response_time, 3),
            'total_requests': total_requests,
            'failed_requests': failed_requests,
            'error_rate': round(error_rate, 2)
        }


class StatusPageService:
    """Service for status page operations"""
    
    def get_overall_status(self) -> str:
        """Get overall system status"""
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        
        if not endpoints.exists():
            return 'operational'
        
        # Check for major outages
        major_outage_count = endpoints.filter(current_status='major_outage').count()
        if major_outage_count > 0:
            return 'major_outage'
        
        # Check for partial outages
        partial_outage_count = endpoints.filter(current_status='partial_outage').count()
        if partial_outage_count > 0:
            return 'partial_outage'
        
        # Check for degraded performance
        degraded_count = endpoints.filter(current_status='degraded').count()
        if degraded_count > 0:
            return 'degraded'
        
        # Check for maintenance
        maintenance_count = endpoints.filter(current_status='maintenance').count()
        if maintenance_count > 0:
            return 'maintenance'
        
        return 'operational'
    
    def get_status_summary(self) -> Dict:
        """Get comprehensive status summary"""
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        overall_status = self.get_overall_status()
        
        # Recent incidents
        recent_incidents = StatusPageIncident.objects.filter(
            is_public=True,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:5]
        
        # System metrics
        metrics_service = SystemMetricsService()
        system_overview = metrics_service.get_system_overview(24)
        
        return {
            'overall_status': overall_status,
            'total_endpoints': endpoints.count(),
            'operational_endpoints': endpoints.filter(current_status='operational').count(),
            'degraded_endpoints': endpoints.filter(current_status='degraded').count(),
            'outage_endpoints': endpoints.filter(
                current_status__in=['partial_outage', 'major_outage']
            ).count(),
            'maintenance_endpoints': endpoints.filter(current_status='maintenance').count(),
            'recent_incidents': [
                {
                    'title': incident.title,
                    'status': incident.status,
                    'severity': incident.severity,
                    'created_at': incident.created_at,
                    'duration': str(incident.duration) if incident.duration else None
                }
                for incident in recent_incidents
            ],
            'system_metrics': system_overview
        }
    
    def create_incident(self, title: str, description: str, severity: str = 'medium', 
                       affected_endpoint_ids: List[int] = None) -> StatusPageIncident:
        """Create a new incident"""
        incident = StatusPageIncident.objects.create(
            title=title,
            description=description,
            severity=severity,
            started_at=timezone.now()
        )
        
        if affected_endpoint_ids:
            endpoints = ServiceEndpoint.objects.filter(id__in=affected_endpoint_ids)
            incident.affected_endpoints.set(endpoints)
        
        return incident


# Global service instances
health_check_service = HealthCheckService()
system_metrics_service = SystemMetricsService()
status_page_service = StatusPageService()