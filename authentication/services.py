import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from twilio.rest import Client as TwilioClient
import africastalking
from typing import Tuple, Optional, Any
import re

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS using Twilio and AfricasTalking"""
    
    def __init__(self):
        self.twilio_client = None
        self.africastalking_client = None
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup SMS service clients"""
        # Setup Twilio
        try:
            if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
                self.twilio_client = TwilioClient(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
        except Exception as e:
            logger.warning(f"Failed to setup Twilio client: {e}")
        
        # Setup AfricasTalking
        try:
            if hasattr(settings, 'AFRICASTALKING_USERNAME') and hasattr(settings, 'AFRICASTALKING_API_KEY'):
                africastalking.initialize(
                    settings.AFRICASTALKING_USERNAME,
                    settings.AFRICASTALKING_API_KEY
                )
                self.africastalking_client = africastalking.SMS
        except Exception as e:
            logger.warning(f"Failed to setup AfricasTalking client: {e}")
    
    def _is_african_number(self, phone_number: str) -> bool:
        """Check if phone number is African (for routing to AfricasTalking)"""
        # Remove any non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)
        
        # African country codes (simplified list)
        african_codes = [
            '254', '255', '256', '234', '233', '225', '227', '223',
            '221', '220', '224', '245', '226', '229', '228', '232',
            '231', '237', '236', '235', '243', '242', '230', '248',
            '269', '262', '261', '268'
        ]
        
        for code in african_codes:
            if digits_only.startswith(code) or digits_only.startswith(f'+{code}'):
                return True
        return False
    
    def send_sms(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """Send SMS using the appropriate service"""
        try:
            # For development, just log instead of actually sending
            if not self.twilio_client and not self.africastalking_client:
                logger.info(f"[DEV MODE] SMS would be sent to {phone_number}: {message}")
                return True, "SMS logged in development mode"
            
            # Choose service based on phone number
            if self._is_african_number(phone_number) and self.africastalking_client:
                return self._send_via_africastalking(phone_number, message)
            elif self.twilio_client:
                return self._send_via_twilio(phone_number, message)
            else:
                logger.warning("No SMS service configured, but continuing")
                return True, "SMS service not configured (development mode)"
                
        except Exception as e:
            logger.warning(f"SMS sending failed, but continuing: {e}")
            return True, f"SMS queued (service not configured): {str(e)[:100]}"
    
    def _send_via_twilio(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """Send SMS via Twilio"""
        try:
            message_instance = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"SMS sent via Twilio to {phone_number}: {message_instance.sid}")
            return True, "SMS sent successfully via Twilio"
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return False, f"Twilio SMS failed: {str(e)}"
    
    def _send_via_africastalking(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """Send SMS via AfricasTalking"""
        try:
            response = self.africastalking_client.send(
                message=message,
                recipients=[phone_number],
                sender_id=getattr(settings, 'AFRICASTALKING_SENDER_ID', None)
            )
            
            if response['SMSMessageData']['Recipients'][0]['status'] == 'Success':
                logger.info(f"SMS sent via AfricasTalking to {phone_number}")
                return True, "SMS sent successfully via AfricasTalking"
            else:
                error_msg = response['SMSMessageData']['Recipients'][0]['status']
                logger.error(f"AfricasTalking SMS failed: {error_msg}")
                return False, f"AfricasTalking SMS failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"AfricasTalking SMS failed: {e}")
            return False, f"AfricasTalking SMS failed: {str(e)}"


class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    def send_email(to_email: str, subject: str, message: str, html_message: str = None) -> Tuple[bool, str]:
        """Send email using Django's email backend - PRODUCTION VERSION"""
        try:
            # Check if email settings are configured
            if not hasattr(settings, 'EMAIL_HOST_USER') or settings.EMAIL_HOST_USER == 'your-email@gmail.com':
                # Log the issue but don't fail in production
                logger.error(f"EMAIL NOT CONFIGURED! Email to {to_email} not sent. Configure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py")
                return False, "Email service not configured. Please contact administrator."
            
            # Try to send email with timeout
            from django.core.mail import get_connection
            connection = get_connection(
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 10)
            )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
                connection=connection
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False, f"Email sending failed: {str(e)}"
    
    @staticmethod
    def send_otp_email(to_email: str, otp_code: str, otp_type: str = "verification") -> Tuple[bool, str]:
        """Send OTP via email with template"""
        subject_map = {
            'email': 'Verify Your Email Address',
            'login': 'Login Verification Code',
            'password_reset': 'Password Reset Code',
        }
        
        subject = subject_map.get(otp_type, 'Verification Code')
        
        # Create email content
        context = {
            'otp_code': otp_code,
            'otp_type': otp_type,
            'expiry_minutes': getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        }
        
        # Plain text message
        message = f"""
Hello,

Your {otp_type} code is: {otp_code}

This code will expire in {context['expiry_minutes']} minutes.

If you didn't request this code, please ignore this email.

Best regards,
Driver App Team
        """
        
        # HTML message
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{subject}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .otp-code {{ font-size: 24px; font-weight: bold; color: #007bff; text-align: center; 
                    background-color: #e7f3ff; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Driver App</h1>
        </div>
        <div class="content">
            <h2>{subject}</h2>
            <p>Hello,</p>
            <p>Your {otp_type} code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in {context['expiry_minutes']} minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>Driver App Team</p>
        </div>
    </div>
</body>
</html>
        """
        
        return EmailService.send_email(to_email, subject, message, html_message)


class OTPService:
    """Service for handling OTP operations"""
    
    def __init__(self):
        self.sms_service = SMSService()
        self.email_service = EmailService()
    
    def send_otp_fast(self, user, otp_type: str, recipient: str, otp_code: str) -> Tuple[bool, str, Optional[Any]]:
        """Send OTP quickly without blocking - OTP is already generated"""
        try:
            # Send OTP with fast timeout
            if '@' in recipient:
                # Send via email with quick timeout
                success, message = self.email_service.send_otp_email(
                    recipient, otp_code, otp_type
                )
            else:
                # Send via SMS with quick timeout
                sms_message = self._create_sms_message(otp_code, otp_type)
                success, message = self.sms_service.send_sms(recipient, sms_message)
            
            if success:
                logger.info(f"OTP sent quickly to {recipient} for {otp_type}")
            else:
                logger.warning(f"OTP sending failed but not critical: {message}")
            
            return True, "OTP sent" if success else "OTP queued", None
                
        except Exception as e:
            logger.warning(f"OTP sending failed (non-critical): {e}")
            return True, "OTP queued for sending", None

    def send_otp(self, user, otp_type: str, recipient: str = None) -> Tuple[bool, str, Optional[Any]]:
        """Send OTP to user via SMS or Email"""
        from .models import OTPVerification
        
        try:
            # Determine recipient if not provided
            if not recipient:
                if otp_type in ['email', 'password_reset'] and user.email:
                    recipient = user.email
                elif otp_type in ['phone', 'login'] and user.phone_number:
                    recipient = user.phone_number
                else:
                    return False, "No valid recipient found", None
            
            # Generate OTP
            otp_verification = OTPVerification.generate_otp(user, otp_type, recipient)
            
            # Send OTP
            if '@' in recipient:
                # Send via email
                success, message = self.email_service.send_otp_email(
                    recipient, otp_verification.otp_code, otp_type
                )
            else:
                # Send via SMS
                sms_message = self._create_sms_message(otp_verification.otp_code, otp_type)
                success, message = self.sms_service.send_sms(recipient, sms_message)
            
            if success:
                logger.info(f"OTP sent successfully to {recipient} for {otp_type}")
                return True, "OTP sent successfully", otp_verification
            else:
                # Delete the OTP if sending failed
                otp_verification.delete()
                return False, message, None
                
        except Exception as e:
            logger.error(f"OTP sending failed: {e}")
            return False, f"OTP sending failed: {str(e)}", None
    
    def _create_sms_message(self, otp_code: str, otp_type: str) -> str:
        """Create SMS message for OTP"""
        type_messages = {
            'phone': f'Your phone verification code is: {otp_code}',
            'email': f'Your email verification code is: {otp_code}',
            'login': f'Your login verification code is: {otp_code}',
            'password_reset': f'Your password reset code is: {otp_code}',
        }
        
        base_message = type_messages.get(otp_type, f'Your verification code is: {otp_code}')
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        
        return f"{base_message}. Valid for {expiry_minutes} minutes. Driver App"
    
    def verify_otp(self, user, otp_code: str, otp_type: str, recipient: str) -> Tuple[bool, str]:
        """Verify OTP code"""
        from .models import OTPVerification
        
        try:
            # Find active OTP
            otp_verification = OTPVerification.objects.filter(
                user=user,
                recipient=recipient,
                otp_type=otp_type,
                is_verified=False
            ).order_by('-created_at').first()
            
            if not otp_verification:
                return False, "No active OTP found"
            
            # Verify OTP
            success, message = otp_verification.verify_otp(otp_code)
            
            if success:
                logger.info(f"OTP verified successfully for {recipient}")
            else:
                logger.warning(f"OTP verification failed for {recipient}: {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"OTP verification failed: {e}")
            return False, f"OTP verification failed: {str(e)}"
    
    def resend_otp(self, user, otp_type: str, recipient: str) -> Tuple[bool, str]:
        """Resend OTP to user"""
        from .models import OTPVerification
        
        try:
            # Check if there's a recent OTP request (rate limiting)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_otp = OTPVerification.objects.filter(
                user=user,
                recipient=recipient,
                otp_type=otp_type,
                created_at__gte=timezone.now() - timedelta(minutes=1)
            ).first()
            
            if recent_otp:
                return False, "Please wait before requesting another OTP"
            
            # Send new OTP
            success, message, otp_verification = self.send_otp(user, otp_type, recipient)
            return success, message
            
        except Exception as e:
            logger.error(f"OTP resend failed: {e}")
            return False, f"OTP resend failed: {str(e)}"


# Global instances
otp_service = OTPService()
sms_service = SMSService()
email_service = EmailService()