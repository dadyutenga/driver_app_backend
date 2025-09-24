from django.core.management.base import BaseCommand
from health.models import ServiceEndpoint, StatusPageSettings


class Command(BaseCommand):
    help = 'Setup health monitoring with sample endpoints'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up health monitoring...'))
        
        # Create status page settings
        settings, created = StatusPageSettings.objects.get_or_create(
            pk=1,
            defaults={
                'page_title': 'Driver App Status',
                'page_description': 'Current status and uptime of Driver App services',
                'company_name': 'Driver App',
                'show_response_times': True,
                'show_uptime_percentage': True,
                'show_incident_history': True,
                'refresh_interval_seconds': 60,
                'primary_color': '#3b82f6',
                'success_color': '#10b981',
                'warning_color': '#f59e0b',
                'danger_color': '#ef4444',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Status page settings created'))
        else:
            self.stdout.write(self.style.WARNING('✓ Status page settings already exist'))
        
        # Define sample endpoints to monitor
        endpoints = [
            {
                'name': 'API Root',
                'description': 'Main API endpoint',
                'url_path': '/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 2,
            },
            {
                'name': 'Health Check',
                'description': 'Basic health check endpoint',
                'url_path': '/health/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 1,
            },
            {
                'name': 'User Registration',
                'description': 'User registration endpoint',
                'url_path': '/api/v1/auth/register/',
                'method': 'POST',
                'expected_status_code': 400,  # Expect 400 without data
                'check_interval_minutes': 5,
            },
            {
                'name': 'User Login',
                'description': 'User login endpoint',
                'url_path': '/api/v1/auth/login/',
                'method': 'POST',
                'expected_status_code': 400,  # Expect 400 without data
                'check_interval_minutes': 5,
            },
            {
                'name': 'OAuth Applications',
                'description': 'OAuth applications endpoint',
                'url_path': '/api/v1/auth/oauth/applications/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 10,
            },
            {
                'name': 'Health Overview API',
                'description': 'Health monitoring overview API',
                'url_path': '/health/api/overview/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 5,
            },
            {
                'name': 'Status Page',
                'description': 'Public status page',
                'url_path': '/health/status-page/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 5,
            },
            {
                'name': 'Admin Panel',
                'description': 'Django admin interface',
                'url_path': '/admin/',
                'method': 'GET',
                'expected_status_code': 200,
                'check_interval_minutes': 10,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for endpoint_data in endpoints:
            endpoint, created = ServiceEndpoint.objects.get_or_create(
                name=endpoint_data['name'],
                defaults=endpoint_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created endpoint: {endpoint.name}')
                )
            else:
                # Update existing endpoint if needed
                updated = False
                for field, value in endpoint_data.items():
                    if field != 'name' and getattr(endpoint, field) != value:
                        setattr(endpoint, field, value)
                        updated = True
                
                if updated:
                    endpoint.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'✓ Updated endpoint: {endpoint.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'✓ Endpoint exists: {endpoint.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nHealth monitoring setup completed!'
                f'\n- Created: {created_count} endpoints'
                f'\n- Updated: {updated_count} endpoints'
                f'\n- Total monitored endpoints: {ServiceEndpoint.objects.count()}'
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nNext steps:'
                f'\n1. Visit the status page at: http://localhost:8000/health/status-page/'
                f'\n2. Check health API at: http://localhost:8000/health/'
                f'\n3. Run health checks manually: python manage.py run_health_checks'
                f'\n4. Start Celery worker for background monitoring:'
                f'\n   celery -A driver_app_backend worker -l info'
                f'\n5. Start Celery beat for scheduled tasks:'
                f'\n   celery -A driver_app_backend beat -l info'
            )
        )