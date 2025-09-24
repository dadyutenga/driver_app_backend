from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, OTPVerification, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = ('email', 'phone_number', 'full_name', 'is_active', 
                   'email_verified', 'phone_verified', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'email_verified', 
                  'phone_verified', 'date_joined')
    search_fields = ('email', 'phone_number', 'full_name')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)
    
    fieldsets = (
        (None, {'fields': ('email', 'phone_number', 'password')}),
        (_('Personal info'), {'fields': ('full_name',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Verification'), {'fields': ('email_verified', 'phone_verified')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'full_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('date_joined', 'updated_at')


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """OTP Verification Admin"""
    
    list_display = ('user', 'otp_type', 'recipient', 'otp_code', 'is_verified', 
                   'attempts', 'created_at', 'expires_at')
    list_filter = ('otp_type', 'is_verified', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'recipient')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'verified_at', 'expires_at')
    
    fieldsets = (
        (None, {'fields': ('user', 'otp_type', 'recipient')}),
        ('OTP Details', {'fields': ('otp_code', 'is_verified', 'attempts', 'max_attempts')}),
        ('Timestamps', {'fields': ('created_at', 'expires_at', 'verified_at')}),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """User Session Admin"""
    
    list_display = ('user', 'ip_address', 'is_active', 'login_at', 
                   'last_activity', 'logout_at')
    list_filter = ('is_active', 'login_at')
    search_fields = ('user__email', 'user__phone_number', 'ip_address')
    ordering = ('-login_at',)
    readonly_fields = ('login_at', 'last_activity', 'logout_at')
    
    fieldsets = (
        (None, {'fields': ('user', 'session_key', 'is_active')}),
        ('Client Info', {'fields': ('ip_address', 'user_agent', 'device_info')}),
        ('Timestamps', {'fields': ('login_at', 'last_activity', 'logout_at')}),
    )
