from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
import logging

from .models import User, OTPVerification, UserSession
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, OTPVerificationSerializer,
    OTPRequestSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
    UserSerializer, UserProfileUpdateSerializer, ChangePasswordSerializer
)
from .services import otp_service

logger = logging.getLogger(__name__)


class UserRegistrationView(APIView):
    """User Registration API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Register a new user"""
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                # Use database transaction for atomic operations
                with transaction.atomic():
                    user = serializer.save()
                
                    # Pre-generate OTP in the database (fast operation)
                    identifier = user.email or user.phone_number
                    otp_type = 'email' if user.email else 'phone'
                    
                    # Generate OTP verification record
                    from .models import OTPVerification
                    otp_verification = OTPVerification.generate_otp(user, otp_type, identifier)
                
                # Send OTP asynchronously (don't wait for email/SMS)
                # The OTP is already saved, so sending can happen in background
                try:
                    success, message, _ = otp_service.send_otp_fast(
                        user, otp_type, identifier, otp_verification.otp_code
                    )
                except Exception as e:
                    logger.warning(f"OTP sending failed but user created: {e}")
                    success, message = True, "Account created. OTP will be sent shortly."
                
                user_data = UserSerializer(user).data
                
                return Response({
                    'success': True,
                    'message': 'User registered successfully. Please verify your account.',
                    'user': user_data,
                    'otp_sent': success,
                    'otp_message': message,
                    'verification_required': True
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return Response({
                'success': False,
                'message': 'Registration failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginView(APIView):
    """User Login API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Login user and return JWT tokens"""
        try:
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                
                # Create JWT tokens
                refresh = RefreshToken.for_user(user)
                access = refresh.access_token
                
                # Create user session
                self._create_user_session(user, request)
                
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(access),
                        'refresh': str(refresh),
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return Response({
                'success': False,
                'message': 'Login failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_user_session(self, user, request):
        """Create user session record"""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or '',
                ip_address=ip_address,
                user_agent=user_agent,
                device_info={}
            )
        except Exception as e:
            logger.warning(f"Failed to create user session: {e}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class OTPVerificationView(APIView):
    """OTP Verification API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Verify OTP code"""
        try:
            serializer = OTPVerificationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                otp_verification = serializer.validated_data['otp_verification']
                otp_code = serializer.validated_data['otp_code']
                
                success, message = otp_verification.verify_otp(otp_code)
                
                if success:
                    # Create JWT tokens after successful verification
                    refresh = RefreshToken.for_user(user)
                    access = refresh.access_token
                    
                    return Response({
                        'success': True,
                        'message': message,
                        'user': UserSerializer(user).data,
                        'tokens': {
                            'access': str(access),
                            'refresh': str(refresh),
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': message
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return Response({
                'success': False,
                'message': 'OTP verification failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPRequestView(APIView):
    """Request/Resend OTP API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Request or resend OTP"""
        try:
            serializer = OTPRequestSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                identifier = serializer.validated_data['identifier']
                otp_type = serializer.validated_data['otp_type']
                
                success, message = otp_service.resend_otp(user, otp_type, identifier)
                
                return Response({
                    'success': success,
                    'message': message
                }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"OTP request error: {e}")
            return Response({
                'success': False,
                'message': 'OTP request failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetView(APIView):
    """Password Reset Request API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Request password reset OTP"""
        try:
            serializer = PasswordResetSerializer(data=request.data)
            if serializer.is_valid():
                identifier = serializer.validated_data['identifier']
                
                # Find user
                user = None
                if '@' in identifier:
                    user = User.objects.filter(email=identifier).first()
                else:
                    user = User.objects.filter(phone_number=identifier).first()
                
                if user:
                    success, message, otp_verification = otp_service.send_otp(
                        user, 'password_reset', identifier
                    )
                    
                    return Response({
                        'success': success,
                        'message': 'Password reset code sent to your email/phone' if success else message
                    }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
                
                # Always return success for security (don't reveal if user exists)
                return Response({
                    'success': True,
                    'message': 'If the account exists, a password reset code has been sent'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return Response({
                'success': False,
                'message': 'Password reset request failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmView(APIView):
    """Password Reset Confirmation API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Confirm password reset with OTP"""
        try:
            serializer = PasswordResetConfirmSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                otp_verification = serializer.validated_data['otp_verification']
                otp_code = serializer.validated_data['otp_code']
                new_password = serializer.validated_data['new_password']
                
                # Verify OTP
                success, message = otp_verification.verify_otp(otp_code)
                
                if success:
                    # Update password
                    user.set_password(new_password)
                    user.save()
                    
                    # Invalidate all user sessions
                    UserSession.objects.filter(user=user, is_active=True).update(
                        is_active=False,
                        logout_at=timezone.now()
                    )
                    
                    return Response({
                        'success': True,
                        'message': 'Password reset successful'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': message
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Password reset confirm error: {e}")
            return Response({
                'success': False,
                'message': 'Password reset confirmation failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User Profile API"""
    
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserProfileUpdateSerializer
    
    def update(self, request, *args, **kwargs):
        """Update user profile"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                old_email = instance.email
                old_phone = instance.phone_number
                
                user = serializer.save()
                
                # Check if email or phone changed and send verification
                verification_messages = []
                
                if old_email != user.email and user.email:
                    user.email_verified = False
                    user.save()
                    success, message, _ = otp_service.send_otp(user, 'email', user.email)
                    if success:
                        verification_messages.append("Verification email sent to new email address")
                
                if old_phone != user.phone_number and user.phone_number:
                    user.phone_verified = False
                    user.save()
                    success, message, _ = otp_service.send_otp(user, 'phone', user.phone_number)
                    if success:
                        verification_messages.append("Verification SMS sent to new phone number")
                
                response_data = {
                    'success': True,
                    'message': 'Profile updated successfully',
                    'user': UserSerializer(user).data
                }
                
                if verification_messages:
                    response_data['verification_messages'] = verification_messages
                
                return Response(response_data, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return Response({
                'success': False,
                'message': 'Profile update failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordView(APIView):
    """Change Password API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change user password"""
        try:
            serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                user = request.user
                new_password = serializer.validated_data['new_password']
                
                # Update password
                user.set_password(new_password)
                user.save()
                
                # Invalidate all user sessions except current
                UserSession.objects.filter(user=user, is_active=True).exclude(
                    session_key=request.session.session_key
                ).update(
                    is_active=False,
                    logout_at=timezone.now()
                )
                
                return Response({
                    'success': True,
                    'message': 'Password changed successfully'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Change password error: {e}")
            return Response({
                'success': False,
                'message': 'Password change failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """User Logout API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user"""
        try:
            # Blacklist refresh token if provided
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.warning(f"Failed to blacklist refresh token: {e}")
            
            # Update user session
            UserSession.objects.filter(
                user=request.user,
                session_key=request.session.session_key,
                is_active=True
            ).update(
                is_active=False,
                logout_at=timezone.now()
            )
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                'success': False,
                'message': 'Logout failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_sessions(request):
    """Get user active sessions"""
    try:
        sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-last_activity')
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'uuid': session.uuid,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'login_at': session.login_at,
                'last_activity': session.last_activity,
                'is_current': session.session_key == request.session.session_key
            })
        
        return Response({
            'success': True,
            'sessions': sessions_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve sessions',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def terminate_session(request, session_uuid):
    """Terminate specific user session"""
    try:
        session = UserSession.objects.get(
            uuid=session_uuid,
            user=request.user,
            is_active=True
        )
        
        session.is_active = False
        session.logout_at = timezone.now()
        session.save()
        
        return Response({
            'success': True,
            'message': 'Session terminated successfully'
        }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Terminate session error: {e}")
        return Response({
            'success': False,
            'message': 'Failed to terminate session',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
