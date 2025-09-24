from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction, models

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix admin users and create superuser if needed'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email', 
            type=str, 
            help='Email for the admin user'
        )
        parser.add_argument(
            '--password', 
            type=str, 
            help='Password for the admin user'
        )
        parser.add_argument(
            '--create', 
            action='store_true',
            help='Create new superuser if not exists'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔧 Fixing Admin Users...")
        
        # Fix existing users that should be admins
        fixed_users = []
        
        # Look for users that might be admins but missing staff status
        potential_admins = User.objects.filter(
            models.Q(email__icontains='admin') |
            models.Q(full_name__icontains='admin') |
            models.Q(is_superuser=True)
        )
        
        for user in potential_admins:
            if not user.is_staff:
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                fixed_users.append(user.email or user.phone_number)
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Fixed admin permissions for: {user.email or user.phone_number}")
                )
        
        if not fixed_users:
            self.stdout.write("ℹ️  No existing users needed fixing")
        
        # Create new superuser if requested
        if options['create']:
            email = options.get('email')
            password = options.get('password')
            
            if not email:
                email = input("Enter admin email: ")
            if not password:
                import getpass
                password = getpass.getpass("Enter admin password: ")
            
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠️  User with email {email} already exists")
                )
            else:
                try:
                    with transaction.atomic():
                        admin_user = User.objects.create_user(
                            email=email,
                            password=password,
                            full_name='Admin User'
                        )
                        admin_user.is_staff = True
                        admin_user.is_superuser = True
                        admin_user.is_active = True
                        admin_user.email_verified = True
                        admin_user.save()
                        
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Created new superuser: {email}")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Failed to create superuser: {e}")
                    )
        
        # Show all admin users
        admin_users = User.objects.filter(is_staff=True)
        self.stdout.write("\n📋 Current Admin Users:")
        for user in admin_users:
            status = "✅" if user.is_active else "❌"
            self.stdout.write(f"  {status} {user.email or user.phone_number} (Staff: {user.is_staff}, Super: {user.is_superuser})")
        
        self.stdout.write(
            self.style.SUCCESS("\n🎉 Admin user fix complete! You should now be able to login to Django admin.")
        )