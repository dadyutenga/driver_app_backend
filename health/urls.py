from django.urls import path, include
from . import views

app_name = 'health'

urlpatterns = [
    # Public status page (HTML)
    path('status-page/', views.status_page_view, name='status_page'),
    path('status-page-api/', views.status_page_api, name='status_page_api'),
    
    # Health API endpoints
    path('api/overview/', views.HealthOverviewView.as_view(), name='health_overview'),
    path('api/endpoints/', views.EndpointHealthView.as_view(), name='endpoints_health'),
    path('api/endpoints/<int:endpoint_id>/', views.EndpointHealthView.as_view(), name='endpoint_health'),
    
    # System metrics API
    path('api/metrics/', views.SystemMetricsView.as_view(), name='system_metrics'),
    
    # Request logs API
    path('api/logs/', views.RequestLogsView.as_view(), name='request_logs'),
    
    # Incidents API
    path('api/incidents/', views.IncidentsView.as_view(), name='incidents'),
    
    # Manual operations
    path('api/run-health-checks/', views.run_health_checks, name='run_health_checks'),
]