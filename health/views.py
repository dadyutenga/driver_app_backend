from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import timedelta
import logging

from .models import (
    ServiceEndpoint, HealthCheck, SystemMetrics, 
    APIRequestLog, StatusPageIncident, StatusPageSettings
)
from .services import (
    health_check_service, system_metrics_service, status_page_service
)
from .serializers import (
    ServiceEndpointSerializer, HealthCheckSerializer, SystemMetricsSerializer,
    APIRequestLogSerializer, StatusPageIncidentSerializer
)

logger = logging.getLogger(__name__)


class HealthOverviewView(APIView):
    """API endpoint for health overview"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get health overview"""
        try:
            status_summary = status_page_service.get_status_summary()
            
            return Response({
                'success': True,
                'data': status_summary
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Health overview error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EndpointHealthView(APIView):
    """API endpoint for individual endpoint health"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, endpoint_id=None):
        """Get health status for all endpoints or specific endpoint"""
        try:
            hours = int(request.GET.get('hours', 24))
            
            if endpoint_id:
                # Get specific endpoint health
                endpoint = get_object_or_404(ServiceEndpoint, id=endpoint_id)
                metrics = health_check_service.get_endpoint_metrics(endpoint, hours)
                
                return Response({
                    'success': True,
                    'endpoint': ServiceEndpointSerializer(endpoint).data,
                    'metrics': metrics
                }, status=status.HTTP_200_OK)
            else:
                # Get all endpoints health
                endpoints = ServiceEndpoint.objects.filter(is_active=True)
                endpoint_data = []
                
                for endpoint in endpoints:
                    metrics = health_check_service.get_endpoint_metrics(endpoint, hours)
                    endpoint_info = ServiceEndpointSerializer(endpoint).data
                    endpoint_info['metrics'] = metrics
                    endpoint_data.append(endpoint_info)
                
                return Response({
                    'success': True,
                    'endpoints': endpoint_data
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Endpoint health error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SystemMetricsView(APIView):
    """API endpoint for system metrics"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get system metrics"""
        try:
            hours = int(request.GET.get('hours', 24))
            
            # Get system overview
            overview = system_metrics_service.get_system_overview(hours)
            
            # Get recent metrics for charts
            since = timezone.now() - timedelta(hours=hours)
            recent_metrics = SystemMetrics.objects.filter(
                timestamp__gte=since
            ).order_by('-timestamp')[:50]
            
            metrics_data = SystemMetricsSerializer(recent_metrics, many=True).data
            
            return Response({
                'success': True,
                'overview': overview,
                'metrics': metrics_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"System metrics error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Manually collect system metrics"""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Staff permissions required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            metrics = system_metrics_service.collect_metrics()
            
            return Response({
                'success': True,
                'message': 'Metrics collected successfully',
                'metrics': SystemMetricsSerializer(metrics).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Manual metrics collection error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RequestLogsView(APIView):
    """API endpoint for request logs"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get API request logs"""
        try:
            # Query parameters
            hours = int(request.GET.get('hours', 24))
            status_code = request.GET.get('status_code')
            path = request.GET.get('path')
            errors_only = request.GET.get('errors_only') == 'true'
            
            # Base query
            since = timezone.now() - timedelta(hours=hours)
            logs = APIRequestLog.objects.filter(timestamp__gte=since)
            
            # Apply filters
            if status_code:
                logs = logs.filter(status_code=int(status_code))
            
            if path:
                logs = logs.filter(path__icontains=path)
            
            if errors_only:
                logs = logs.filter(status_code__gte=400)
            
            # Get paginated results
            page_size = int(request.GET.get('page_size', 100))
            logs = logs.order_by('-timestamp')[:page_size]
            
            # Statistics
            stats = {
                'total_requests': APIRequestLog.objects.filter(timestamp__gte=since).count(),
                'error_requests': APIRequestLog.objects.filter(
                    timestamp__gte=since, 
                    status_code__gte=400
                ).count(),
                'avg_response_time': APIRequestLog.objects.filter(
                    timestamp__gte=since
                ).aggregate(avg_time=Avg('response_time'))['avg_time'] or 0.0,
                'slow_requests': APIRequestLog.objects.filter(
                    timestamp__gte=since,
                    response_time__gt=2.0
                ).count()
            }
            
            return Response({
                'success': True,
                'logs': APIRequestLogSerializer(logs, many=True).data,
                'statistics': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Request logs error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IncidentsView(APIView):
    """API endpoint for incidents management"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get incidents"""
        try:
            # Query parameters
            is_public = request.GET.get('public_only') == 'true'
            days = int(request.GET.get('days', 30))
            
            since = timezone.now() - timedelta(days=days)
            incidents = StatusPageIncident.objects.filter(created_at__gte=since)
            
            if is_public:
                incidents = incidents.filter(is_public=True)
            
            incidents = incidents.order_by('-created_at')
            
            return Response({
                'success': True,
                'incidents': StatusPageIncidentSerializer(incidents, many=True).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Incidents view error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create new incident"""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Staff permissions required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            data = request.data
            incident = status_page_service.create_incident(
                title=data.get('title'),
                description=data.get('description'),
                severity=data.get('severity', 'medium'),
                affected_endpoint_ids=data.get('affected_endpoints', [])
            )
            
            incident.created_by = request.user
            incident.save()
            
            return Response({
                'success': True,
                'message': 'Incident created successfully',
                'incident': StatusPageIncidentSerializer(incident).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Create incident error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def run_health_checks(request):
    """Manually trigger health checks"""
    if not request.user.is_staff:
        return Response({
            'success': False,
            'error': 'Staff permissions required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        results = health_check_service.check_all_endpoints()
        
        return Response({
            'success': True,
            'message': f'Health checks completed for {len(results)} endpoints',
            'results': [
                {
                    'endpoint': result.endpoint.name,
                    'is_healthy': result.is_healthy,
                    'response_time': result.response_time,
                    'status_code': result.status_code,
                    'error_message': result.error_message
                }
                for result in results
            ]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Manual health checks error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def status_page_view(request):
    """Public status page view"""
    try:
        # Get status page settings
        settings_obj = StatusPageSettings.get_settings()
        
        # Get status summary
        status_summary = status_page_service.get_status_summary()
        
        # Get endpoints with their metrics
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        endpoint_data = []
        
        for endpoint in endpoints:
            metrics = health_check_service.get_endpoint_metrics(endpoint, 24)
            endpoint_data.append({
                'endpoint': endpoint,
                'metrics': metrics
            })
        
        # Get recent incidents
        recent_incidents = StatusPageIncident.objects.filter(
            is_public=True,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')
        
        context = {
            'settings': settings_obj,
            'status_summary': status_summary,
            'endpoint_data': endpoint_data,
            'recent_incidents': recent_incidents,
            'last_updated': timezone.now(),
        }
        
        return render(request, 'health/status_page.html', context)
        
    except Exception as e:
        logger.error(f"Status page error: {e}")
        return render(request, 'health/status_page_error.html', {'error': str(e)})


def status_page_api(request):
    """Status page data API for AJAX updates"""
    try:
        status_summary = status_page_service.get_status_summary()
        
        return JsonResponse({
            'success': True,
            'data': status_summary,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status page API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)