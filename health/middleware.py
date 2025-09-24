import time
import logging
import json
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from .models import APIRequestLog

User = get_user_model()
logger = logging.getLogger(__name__)


class APIRequestTrackingMiddleware(MiddlewareMixin):
    """Middleware to track API requests and responses for monitoring"""
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process the incoming request"""
        # Skip tracking for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/health/status-page/',  # Avoid infinite loops
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Record start time
        request._monitoring_start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        """Process the response and log the request"""
        # Skip if start time not recorded
        if not hasattr(request, '_monitoring_start_time'):
            return response
        
        try:
            # Calculate response time
            response_time = time.time() - request._monitoring_start_time
            
            # Get client IP
            ip_address = self._get_client_ip(request)
            
            # Get user if authenticated
            user = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
            
            # Get query parameters
            query_params = dict(request.GET.items()) if request.GET else {}
            
            # Get response size
            response_size = len(response.content) if hasattr(response, 'content') else 0
            
            # Get errors from response
            errors = ""
            if response.status_code >= 400:
                if hasattr(response, 'content') and response.content:
                    try:
                        content = response.content.decode('utf-8')
                        if len(content) > 1000:  # Truncate long error messages
                            content = content[:1000] + "..."
                        errors = content
                    except:
                        errors = f"HTTP {response.status_code} Error"
            
            # Create request log
            APIRequestLog.objects.create(
                method=request.method,
                path=request.path,
                user=user,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],  # Truncate long user agents
                status_code=response.status_code,
                response_time=response_time,
                response_size=response_size,
                query_params=query_params,
                errors=errors
            )
            
            # Log slow requests
            if response_time > 2.0:  # Slow request threshold
                logger.warning(
                    f"Slow request detected: {request.method} {request.path} "
                    f"took {response_time:.3f}s (Status: {response.status_code})"
                )
            
            # Log error responses
            if response.status_code >= 500:
                logger.error(
                    f"Server error: {request.method} {request.path} "
                    f"returned {response.status_code} in {response_time:.3f}s"
                )
            
        except Exception as e:
            # Don't let monitoring break the response
            logger.error(f"Error in APIRequestTrackingMiddleware: {e}")
        
        return response
    
    def _get_client_ip(self, request):
        """Get the client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in case of multiple proxies
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """Middleware to provide health check endpoints"""
    
    def process_request(self, request):
        """Handle health check requests"""
        if request.path == '/health/':
            from django.http import JsonResponse
            from .services import system_metrics_service, status_page_service
            
            try:
                # Get overall status
                overall_status = status_page_service.get_overall_status()
                
                # Get basic system metrics
                system_overview = system_metrics_service.get_system_overview(1)  # Last hour
                
                # Database health check
                from django.db import connection
                start_time = time.time()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                db_response_time = time.time() - start_time
                
                health_data = {
                    'status': overall_status,
                    'timestamp': timezone.now().isoformat(),
                    'database': {
                        'status': 'operational' if db_response_time < 1.0 else 'degraded',
                        'response_time': round(db_response_time, 3)
                    },
                    'system': {
                        'cpu_usage': system_overview.get('avg_cpu_usage', 0),
                        'memory_usage': system_overview.get('avg_memory_usage', 0),
                        'error_rate': system_overview.get('error_rate', 0)
                    },
                    'version': '1.0.0'
                }
                
                # Set appropriate HTTP status code
                status_code = 200 if overall_status == 'operational' else 503
                
                return JsonResponse(health_data, status=status_code)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return JsonResponse({
                    'status': 'error',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                }, status=503)
        
        return None


class ResponseTimeHeaderMiddleware(MiddlewareMixin):
    """Middleware to add response time header"""
    
    def process_request(self, request):
        """Record start time"""
        request._response_time_start = time.time()
        return None
    
    def process_response(self, request, response):
        """Add response time header"""
        if hasattr(request, '_response_time_start'):
            response_time = time.time() - request._response_time_start
            response['X-Response-Time'] = f"{response_time:.3f}s"
        
        return response