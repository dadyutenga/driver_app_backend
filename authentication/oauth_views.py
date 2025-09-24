from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from oauth2_provider.models import Application
from django.contrib.auth import authenticate
import requests
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_oauth(request):
    """Google OAuth authentication"""
    try:
        # Get access token from Google
        google_access_token = request.data.get('access_token')
        if not google_access_token:
            return Response({
                'success': False,
                'message': 'Google access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify token with Google
        google_user_info_url = f'https://www.googleapis.com/oauth2/v2/userinfo?access_token={google_access_token}'
        response = requests.get(google_user_info_url)
        
        if response.status_code != 200:
            return Response({
                'success': False,
                'message': 'Invalid Google access token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        google_user_data = response.json()
        
        # Extract user information
        email = google_user_data.get('email')
        full_name = google_user_data.get('name', '')
        google_id = google_user_data.get('id')
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email not provided by Google'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from .models import User
        from .serializers import UserSerializer
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Check if user exists
        user = User.objects.filter(email=email).first()
        
        if user:
            # User exists, log them in
            if not user.is_active:
                user.is_active = True
                user.email_verified = True
                user.save()
        else:
            # Create new user
            user = User.objects.create_user(
                email=email,
                full_name=full_name,
                is_active=True,
                email_verified=True
            )
        
        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        return Response({
            'success': True,
            'message': 'Google OAuth successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(access),
                'refresh': str(refresh),
            },
            'oauth_provider': 'google'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        return Response({
            'success': False,
            'message': 'Google OAuth failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def facebook_oauth(request):
    """Facebook OAuth authentication"""
    try:
        # Get access token from Facebook
        facebook_access_token = request.data.get('access_token')
        if not facebook_access_token:
            return Response({
                'success': False,
                'message': 'Facebook access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify token with Facebook
        facebook_user_info_url = f'https://graph.facebook.com/me?fields=id,name,email&access_token={facebook_access_token}'
        response = requests.get(facebook_user_info_url)
        
        if response.status_code != 200:
            return Response({
                'success': False,
                'message': 'Invalid Facebook access token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        facebook_user_data = response.json()
        
        # Extract user information
        email = facebook_user_data.get('email')
        full_name = facebook_user_data.get('name', '')
        facebook_id = facebook_user_data.get('id')
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email not provided by Facebook'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from .models import User
        from .serializers import UserSerializer
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Check if user exists
        user = User.objects.filter(email=email).first()
        
        if user:
            # User exists, log them in
            if not user.is_active:
                user.is_active = True
                user.email_verified = True
                user.save()
        else:
            # Create new user
            user = User.objects.create_user(
                email=email,
                full_name=full_name,
                is_active=True,
                email_verified=True
            )
        
        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        return Response({
            'success': True,
            'message': 'Facebook OAuth successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(access),
                'refresh': str(refresh),
            },
            'oauth_provider': 'facebook'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Facebook OAuth error: {e}")
        return Response({
            'success': False,
            'message': 'Facebook OAuth failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth_applications(request):
    """Get OAuth applications for the frontend"""
    try:
        applications = Application.objects.filter(user__isnull=True)
        
        apps_data = []
        for app in applications:
            apps_data.append({
                'client_id': app.client_id,
                'name': app.name,
                'client_type': app.client_type,
                'authorization_grant_type': app.authorization_grant_type
            })
        
        return Response({
            'success': True,
            'applications': apps_data,
            'oauth_endpoints': {
                'authorize': '/o/authorize/',
                'token': '/o/token/',
                'revoke_token': '/o/revoke_token/',
                'introspect': '/o/introspect/',
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"OAuth applications error: {e}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve OAuth applications',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)