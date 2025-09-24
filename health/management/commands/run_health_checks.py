from django.core.management.base import BaseCommand
from health.services import health_check_service, system_metrics_service


class Command(BaseCommand):
    help = 'Run health checks on all monitored endpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--endpoint',
            type=str,
            help='Run health check for a specific endpoint by name'
        )
        parser.add_argument(
            '--collect-metrics',
            action='store_true',
            help='Also collect system metrics'
        )

    def handle(self, *args, **options):
        endpoint_name = options.get('endpoint')
        collect_metrics = options.get('collect_metrics')
        
        if endpoint_name:
            # Run health check for specific endpoint
            from health.models import ServiceEndpoint
            
            try:
                endpoint = ServiceEndpoint.objects.get(name=endpoint_name, is_active=True)
                self.stdout.write(f'Running health check for: {endpoint.name}')
                
                result = health_check_service.check_endpoint(endpoint)
                
                if result.is_healthy:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {endpoint.name} is healthy '
                            f'(Response: {result.response_time:.3f}s, Status: {result.status_code})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ {endpoint.name} is unhealthy '
                            f'(Response: {result.response_time:.3f}s, Error: {result.error_message})'
                        )
                    )
                
            except ServiceEndpoint.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Endpoint "{endpoint_name}" not found or inactive')
                )
                return
        else:
            # Run health checks for all endpoints
            self.stdout.write('Running health checks for all active endpoints...')
            
            results = health_check_service.check_all_endpoints()
            
            if not results:
                self.stdout.write(self.style.WARNING('No active endpoints found to check'))
                return
            
            healthy_count = 0
            unhealthy_count = 0
            
            for result in results:
                if result.is_healthy:
                    healthy_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {result.endpoint.name}: {result.response_time:.3f}s '
                            f'(Status: {result.status_code})'
                        )
                    )
                else:
                    unhealthy_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ {result.endpoint.name}: {result.response_time:.3f}s '
                            f'({result.error_message})'
                        )
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nHealth check summary:'
                    f'\n- Total endpoints: {len(results)}'
                    f'\n- Healthy: {healthy_count}'
                    f'\n- Unhealthy: {unhealthy_count}'
                )
            )
        
        # Collect system metrics if requested
        if collect_metrics:
            self.stdout.write('\nCollecting system metrics...')
            try:
                metrics = system_metrics_service.collect_metrics()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ System metrics collected:'
                        f'\n- CPU: {metrics.cpu_usage_percent:.1f}%'
                        f'\n- Memory: {metrics.memory_usage_percent:.1f}%'
                        f'\n- DB Connection: {metrics.db_connection_time:.3f}s'
                        f'\n- Requests (1h): {metrics.total_requests} total, {metrics.failed_requests} failed'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to collect system metrics: {e}')
                )