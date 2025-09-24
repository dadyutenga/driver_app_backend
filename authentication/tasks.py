from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_otp_email_task(self, user_id, otp_code, otp_type, recipient):
    """Celery task to send OTP via email"""
    try:
        from .services import email_service
        
        success, message = email_service.send_otp_email(recipient, otp_code, otp_type)
        
        if success:
            logger.info(f"OTP email sent successfully to {recipient}")
            return {'success': True, 'message': message}
        else:
            logger.error(f"Failed to send OTP email to {recipient}: {message}")
            # Retry the task if it failed
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=60 * (2 ** self.request.retries))
            return {'success': False, 'message': message}
            
    except Exception as e:
        logger.error(f"OTP email task error: {e}")
        # Retry the task if it failed
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {'success': False, 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def send_otp_sms_task(self, user_id, otp_code, otp_type, recipient):
    """Celery task to send OTP via SMS"""
    try:
        from .services import sms_service
        
        # Create SMS message
        type_messages = {
            'phone': f'Your phone verification code is: {otp_code}',
            'email': f'Your email verification code is: {otp_code}',
            'login': f'Your login verification code is: {otp_code}',
            'password_reset': f'Your password reset code is: {otp_code}',
        }
        
        base_message = type_messages.get(otp_type, f'Your verification code is: {otp_code}')
        from django.conf import settings
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        sms_message = f"{base_message}. Valid for {expiry_minutes} minutes. Driver App"
        
        success, message = sms_service.send_sms(recipient, sms_message)
        
        if success:
            logger.info(f"OTP SMS sent successfully to {recipient}")
            return {'success': True, 'message': message}
        else:
            logger.error(f"Failed to send OTP SMS to {recipient}: {message}")
            # Retry the task if it failed
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=60 * (2 ** self.request.retries))
            return {'success': False, 'message': message}
            
    except Exception as e:
        logger.error(f"OTP SMS task error: {e}")
        # Retry the task if it failed
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {'success': False, 'message': str(e)}


@shared_task
def cleanup_expired_otps():
    """Clean up expired OTP records"""
    try:
        from .models import OTPVerification
        
        expired_otps = OTPVerification.objects.filter(
            expires_at__lt=timezone.now(),
            is_verified=False
        )
        
        count = expired_otps.count()
        expired_otps.delete()
        
        logger.info(f"Cleaned up {count} expired OTP records")
        return {'success': True, 'cleaned_count': count}
        
    except Exception as e:
        logger.error(f"OTP cleanup task error: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_sessions():
    """Clean up old user sessions"""
    try:
        from .models import UserSession
        from datetime import timedelta
        
        # Delete sessions older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        old_sessions = UserSession.objects.filter(
            login_at__lt=cutoff_date
        )
        
        count = old_sessions.count()
        old_sessions.delete()
        
        logger.info(f"Cleaned up {count} old session records")
        return {'success': True, 'cleaned_count': count}
        
    except Exception as e:
        logger.error(f"Session cleanup task error: {e}")
        return {'success': False, 'error': str(e)}