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
        """Register a new user (fast path) and issue an OTP challenge (4-char alphanumeric)."""
        start_time = timezone.now()
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Create user in a single transaction; keep user active (2FA via OTP will gate token issuance later).
            with transaction.atomic():
                user = serializer.save()
                if not user.is_active:
                    user.is_active = True  # Active for login but still requires OTP to verify channel
                    user.save(update_fields=['is_active'])

                identifier = user.email or user.phone_number
                otp_type = 'email' if user.email else 'phone'

                # Generate 4-character alphanumeric OTP (digits + uppercase letters) for better entropy but short length
                from django.conf import settings as dj_settings
                import random, string
                otp_length = 4  # Requirement: 4 characters (letter or number)
                alphabet = string.digits + string.ascii_uppercase
                otp_code = ''.join(random.choices(alphabet, k=otp_length))

                # Create OTP record immediately (no background for DB write)
                from datetime import timedelta
                expiry_minutes = getattr(dj_settings, 'OTP_EXPIRY_MINUTES', 10)
                otp_verification = OTPVerification.objects.create(
                    user=user,
                    otp_code=otp_code,
                    otp_type=otp_type,
                    recipient=identifier,
                    expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
                )

            # Background send with retry (max 3 attempts exponential backoff)
            import threading, time as _time

            def send_with_retry():
                attempts = 0
                base_delay = 1.0  # seconds
                while attempts < 3:
                    try:
                        # Decide channel
                        if '@' in identifier:
                            otp_service.email_service.send_otp_email(identifier, otp_code, otp_type)
                        else:
                            msg = otp_service._create_sms_message(otp_code, otp_type)
                            otp_service.sms_service.send_sms(identifier, msg)
                        logger.info(f"OTP dispatch attempt {attempts+1} succeeded for {identifier}")
                        return
                    except Exception as ex:
                        attempts += 1
                        logger.warning(f"OTP dispatch attempt {attempts} failed for {identifier}: {ex}")
                        if attempts < 3:
                            _time.sleep(base_delay * (2 ** (attempts - 1)))
                logger.error(f"All OTP dispatch attempts failed for {identifier}")

            threading.Thread(target=send_with_retry, daemon=True).start()

            user_data = {
                'uuid': str(user.uuid),
                'email': user.email,
                'phone_number': user.phone_number,
                'full_name': user.full_name,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'phone_verified': user.phone_verified,
            }

            elapsed_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            return Response({
                'success': True,
                'message': 'User registered. Enter the OTP sent to your contact.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return Response({'success': False, 'message': 'Registration failed', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginView(APIView):
    """User Login API"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Login user (password step) then issue OTP challenge; tokens only after OTP verification."""
        start_time = timezone.now()
        try:
            serializer = UserLoginSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.validated_data['user']

            # Create (or refresh) a lightweight session record quickly
            try:
                self._create_user_session_fast(user, request)
            except Exception as e:
                logger.warning(f"Session creation deferred: {e}")

            # Determine OTP channel preference: email first, else phone
            identifier = user.email or user.phone_number
            otp_type = 'login'

            # Generate 4-char alphanumeric OTP
            import random, string
            alphabet = string.digits + string.ascii_uppercase
            otp_code = ''.join(random.choices(alphabet, k=4))

            # Create OTP record
            from datetime import timedelta
            expiry_minutes = getattr(__import__('django.conf').conf.settings, 'OTP_EXPIRY_MINUTES', 10)
            otp_verification = OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                otp_type=otp_type,
                recipient=identifier,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
            )

            # Background send with retry
            import threading, time as _time
            def send_with_retry():
                attempts = 0
                base_delay = 1.0
                while attempts < 3:
                    try:
                        if '@' in identifier:
                            otp_service.email_service.send_otp_email(identifier, otp_code, otp_type)
                        else:
                            msg = otp_service._create_sms_message(otp_code, otp_type)
                            otp_service.sms_service.send_sms(identifier, msg)
                        logger.info(f"Login OTP dispatch attempt {attempts+1} OK for {identifier}")
                        return
                    except Exception as ex:
                        attempts += 1
                        logger.warning(f"Login OTP attempt {attempts} failed for {identifier}: {ex}")
                        if attempts < 3:
                            _time.sleep(base_delay * (2 ** (attempts - 1)))
                logger.error(f"All login OTP attempts failed for {identifier}")

            threading.Thread(target=send_with_retry, daemon=True).start()

            elapsed_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            return Response({
                'success': True,
                'message': 'Password accepted. Enter the OTP sent to your contact.',
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Login error: {e}")
            return Response({'success': False, 'message': 'Login failed', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _create_user_session_fast(self, user, request):
        """Create user session record - Optimized"""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]  # Truncate for performance
            
            # Create session without excessive validation
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or f'api-{user.uuid}',
                ip_address=ip_address,
                user_agent=user_agent,
                device_info={}  # Empty dict for speed
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
        """Verify OTP, mark verification, and issue tokens (supports email/phone/login/password_reset)."""
        start_time = timezone.now()
        try:
            identifier = request.data.get('identifier')
            otp_code = request.data.get('otp_code')
            otp_type = request.data.get('otp_type', 'email')
            if not identifier or not otp_code:
                return Response({'success': False, 'message': 'Identifier and OTP code are required'}, status=status.HTTP_400_BAD_REQUEST)

            # Resolve user
            user = User.objects.filter(email=identifier).first() if '@' in identifier else User.objects.filter(phone_number=identifier).first()
            if not user:
                return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Get latest active OTP for this type (login may have otp_type='login')
            otp_qs = OTPVerification.objects.filter(
                user=user,
                recipient=identifier,
                otp_type=otp_type,
                is_verified=False
            ).order_by('-created_at')
            otp_verification = otp_qs.first()
            if not otp_verification:
                return Response({'success': False, 'message': 'No active OTP found'}, status=status.HTTP_400_BAD_REQUEST)

            success, message = otp_verification.verify_otp(otp_code)
            if not success:
                return Response({'success': False, 'message': message}, status=status.HTTP_400_BAD_REQUEST)

            # For login OTPs, we don't change email_verified/phone_verified flags inside model verify for 'login'; ensure user is active
            if otp_type == 'login' and not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

            # Issue tokens (7 day access / 30 day refresh per settings)
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            # Minimal user payload
            user_data = {
                'uuid': str(user.uuid),
                'full_name': user.full_name,
            }
            if user.email:
                user_data['email'] = user.email
            if user.phone_number and not user.email:
                # Only include phone if email absent to keep payload small
                user_data['phone_number'] = user.phone_number
            elapsed_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            return Response({
                'success': True,
                'message': message,
                'user': user_data,
                'tokens': {
                    'access': str(access),
                    'refresh': str(refresh),
                },
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return Response({'success': False, 'message': 'OTP verification failed', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
