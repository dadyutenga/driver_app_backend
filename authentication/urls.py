from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from . import views, oauth_views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # OTP endpoints
    path('verify-otp/', views.OTPVerificationView.as_view(), name='verify_otp'),
    path('request-otp/', views.OTPRequestView.as_view(), name='request_otp'),
    path('resend-otp/', views.OTPRequestView.as_view(), name='resend_otp'),
    
    # Password reset endpoints
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Session management
    path('sessions/', views.user_sessions, name='user_sessions'),
    path('sessions/<uuid:session_uuid>/terminate/', views.terminate_session, name='terminate_session'),
    
    # JWT token endpoints
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # OAuth endpoints
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('oauth/google/', oauth_views.google_oauth, name='google_oauth'),
    path('oauth/facebook/', oauth_views.facebook_oauth, name='facebook_oauth'),
    path('oauth/applications/', oauth_views.oauth_applications, name='oauth_applications'),
]