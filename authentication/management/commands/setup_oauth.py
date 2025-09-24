from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = 'Create OAuth2 applications for the Driver App'

    def handle(self, *args, **options):
        # Create application for web frontend
        web_app, created = Application.objects.get_or_create(
            name="Driver App Web",
            defaults={
                'client_type': Application.CLIENT_PUBLIC,
                'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created web application: {web_app.client_id}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Web application already exists: {web_app.client_id}')
            )
        
        # Create application for mobile app
        mobile_app, created = Application.objects.get_or_create(
            name="Driver App Mobile",
            defaults={
                'client_type': Application.CLIENT_PUBLIC,
                'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created mobile application: {mobile_app.client_id}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Mobile application already exists: {mobile_app.client_id}')
            )
        
        # Create application for third-party integrations
        api_app, created = Application.objects.get_or_create(
            name="Driver App API",
            defaults={
                'client_type': Application.CLIENT_CONFIDENTIAL,
                'authorization_grant_type': Application.GRANT_CLIENT_CREDENTIALS,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created API application: {api_app.client_id}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Client Secret: {api_app.client_secret}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'API application already exists: {api_app.client_id}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\nOAuth2 applications setup completed!')
        )
        self.stdout.write(
            'You can view and manage these applications in the Django admin at /admin/oauth2_provider/application/'
        )