from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import ServiceEndpoint, HealthCheck, SystemMetrics, APIRequestLog
from .services import health_check_service, system_metrics_service

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_health_checks_task(self):
    """Scheduled task to run health checks on all endpoints"""
    try:
        logger.info("Starting scheduled health checks")
        
        # Get all active endpoints
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        
        if not endpoints.exists():
            logger.info("No active endpoints to check")
            return {'success': True, 'message': 'No active endpoints', 'checked': 0}
        
        results = []
        successful_checks = 0
        failed_checks = 0
        
        for endpoint in endpoints:
            try:
                # Check if it's time to check this endpoint
                if endpoint.last_check:
                    next_check_time = endpoint.last_check + timedelta(
                        minutes=endpoint.check_interval_minutes
                    )
                    if timezone.now() < next_check_time:
                        continue  # Skip this endpoint for now
                
                # Perform health check
                health_check = health_check_service.check_endpoint(endpoint)
                
                result = {
                    'endpoint': endpoint.name,
                    'is_healthy': health_check.is_healthy,
                    'response_time': health_check.response_time,
                    'status_code': health_check.status_code,
                    'error_message': health_check.error_message
                }
                results.append(result)
                
                if health_check.is_healthy:
                    successful_checks += 1
                else:
                    failed_checks += 1
                    logger.warning(f"Health check failed for {endpoint.name}: {health_check.error_message}")
                
            except Exception as e:
                logger.error(f"Error checking endpoint {endpoint.name}: {e}")
                results.append({
                    'endpoint': endpoint.name,
                    'is_healthy': False,
                    'error': str(e)
                })
                failed_checks += 1
        
        logger.info(f"Health checks completed: {successful_checks} successful, {failed_checks} failed")
        
        return {
            'success': True,
            'checked': len(results),
            'successful': successful_checks,
            'failed': failed_checks,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Health checks task failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def collect_system_metrics_task(self):
    """Scheduled task to collect system metrics"""
    try:
        logger.info("Collecting system metrics")
        
        metrics = system_metrics_service.collect_metrics()
        
        logger.info(f"System metrics collected: CPU {metrics.cpu_usage_percent}%, Memory {metrics.memory_usage_percent}%")
        
        return {
            'success': True,
            'metrics': {
                'cpu_usage': metrics.cpu_usage_percent,
                'memory_usage': metrics.memory_usage_percent,
                'db_connection_time': metrics.db_connection_time,
                'total_requests': metrics.total_requests,
                'failed_requests': metrics.failed_requests
            }
        }
        
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def cleanup_old_health_data_task(self):
    """Scheduled task to cleanup old health monitoring data"""
    try:
        logger.info("Starting cleanup of old health data")
        
        # Keep health checks for 30 days
        health_check_cutoff = timezone.now() - timedelta(days=30)
        old_health_checks = HealthCheck.objects.filter(timestamp__lt=health_check_cutoff)
        health_checks_count = old_health_checks.count()
        old_health_checks.delete()
        
        # Keep system metrics for 30 days
        metrics_cutoff = timezone.now() - timedelta(days=30)
        old_metrics = SystemMetrics.objects.filter(timestamp__lt=metrics_cutoff)
        metrics_count = old_metrics.count()
        old_metrics.delete()
        
        # Keep API request logs for 7 days
        api_logs_cutoff = timezone.now() - timedelta(days=7)
        old_api_logs = APIRequestLog.objects.filter(timestamp__lt=api_logs_cutoff)
        api_logs_count = old_api_logs.count()
        old_api_logs.delete()
        
        logger.info(f"Cleanup completed: {health_checks_count} health checks, "
                   f"{metrics_count} metrics, {api_logs_count} API logs removed")
        
        return {
            'success': True,
            'cleaned': {
                'health_checks': health_checks_count,
                'system_metrics': metrics_count,
                'api_logs': api_logs_count
            }
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def check_endpoint_alerting_task(self):
    """Task to check for endpoints that need alerting"""
    try:
        logger.info("Checking endpoints for alerting conditions")
        
        alerts_sent = 0
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        
        for endpoint in endpoints:
            try:
                # Check if endpoint has been down for more than 10 minutes
                recent_checks = endpoint.health_checks.filter(
                    timestamp__gte=timezone.now() - timedelta(minutes=10)
                ).order_by('-timestamp')
                
                if recent_checks.exists():
                    failed_checks = [check for check in recent_checks if not check.is_healthy]
                    
                    # If all recent checks failed, send alert
                    if len(failed_checks) == len(recent_checks) and len(recent_checks) >= 3:
                        # Send alert (implement your alerting logic here)
                        logger.warning(f"ALERT: Endpoint {endpoint.name} has been down for 10+ minutes")
                        alerts_sent += 1
                        
                        # You can integrate with email, Slack, PagerDuty, etc.
                        # await send_alert_notification(endpoint, failed_checks)
                
            except Exception as e:
                logger.error(f"Error checking alerts for endpoint {endpoint.name}: {e}")
        
        return {
            'success': True,
            'alerts_checked': endpoints.count(),
            'alerts_sent': alerts_sent
        }
        
    except Exception as e:
        logger.error(f"Alerting task failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def update_endpoint_uptime_task(self):
    """Task to update endpoint uptime percentages"""
    try:
        logger.info("Updating endpoint uptime percentages")
        
        endpoints = ServiceEndpoint.objects.filter(is_active=True)
        updated_count = 0
        
        for endpoint in endpoints:
            try:
                # Update 24-hour uptime
                uptime_24h = endpoint.calculate_uptime(24)
                
                if endpoint.uptime_percentage != uptime_24h:
                    endpoint.uptime_percentage = uptime_24h
                    endpoint.save()
                    updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating uptime for endpoint {endpoint.name}: {e}")
        
        logger.info(f"Updated uptime for {updated_count} endpoints")
        
        return {
            'success': True,
            'endpoints_checked': endpoints.count(),
            'endpoints_updated': updated_count
        }
        
    except Exception as e:
        logger.error(f"Uptime update task failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def generate_daily_report_task(self):
    """Task to generate daily health report"""
    try:
        logger.info("Generating daily health report")
        
        # Get yesterday's date range
        yesterday = timezone.now().date() - timedelta(days=1)
        start_time = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.time.min))
        end_time = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.time.max))
        
        # Collect statistics
        total_checks = HealthCheck.objects.filter(timestamp__range=(start_time, end_time)).count()
        failed_checks = HealthCheck.objects.filter(
            timestamp__range=(start_time, end_time), 
            is_healthy=False
        ).count()
        
        total_requests = APIRequestLog.objects.filter(timestamp__range=(start_time, end_time)).count()
        error_requests = APIRequestLog.objects.filter(
            timestamp__range=(start_time, end_time),
            status_code__gte=400
        ).count()
        
        # Calculate averages
        avg_response_time = APIRequestLog.objects.filter(
            timestamp__range=(start_time, end_time)
        ).aggregate(avg_time=timezone.models.Avg('response_time'))['avg_time'] or 0.0
        
        system_metrics = SystemMetrics.objects.filter(
            timestamp__range=(start_time, end_time)
        )
        
        avg_cpu = system_metrics.aggregate(avg_cpu=timezone.models.Avg('cpu_usage_percent'))['avg_cpu'] or 0.0
        avg_memory = system_metrics.aggregate(avg_memory=timezone.models.Avg('memory_usage_percent'))['avg_memory'] or 0.0
        
        report_data = {
            'date': yesterday.isoformat(),
            'health_checks': {
                'total': total_checks,
                'failed': failed_checks,
                'success_rate': ((total_checks - failed_checks) / total_checks * 100) if total_checks > 0 else 100.0
            },
            'api_requests': {
                'total': total_requests,
                'errors': error_requests,
                'error_rate': (error_requests / total_requests * 100) if total_requests > 0 else 0.0,
                'avg_response_time': round(avg_response_time, 3)
            },
            'system': {
                'avg_cpu_usage': round(avg_cpu, 2),
                'avg_memory_usage': round(avg_memory, 2)
            }
        }
        
        logger.info(f"Daily report generated for {yesterday}: "
                   f"{total_checks} health checks, {total_requests} API requests")
        
        # Here you could save the report to a file or send via email
        # save_daily_report(report_data)
        # send_daily_report_email(report_data)
        
        return {
            'success': True,
            'report': report_data
        }
        
    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")
        return {'success': False, 'error': str(e)}