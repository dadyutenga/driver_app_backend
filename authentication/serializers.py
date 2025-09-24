from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, OTPVerification
import re


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'phone_number', 'full_name', 'password', 'confirm_password')
        
    def validate(self, attrs):
        """Validate registration data"""
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        
        # Check if at least email or phone is provided
        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required")
        
        # Check if password matches confirm_password
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate email uniqueness
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists")
        
        # Validate phone uniqueness
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("User with this phone number already exists")
        
        # Validate phone number format
        if phone_number:
            phone_regex = r'^\+?1?\d{9,15}$'
            if not re.match(phone_regex, phone_number):
                raise serializers.ValidationError("Invalid phone number format")
        
        return attrs
    
    def create(self, validated_data):
        """Create new user"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    identifier = serializers.CharField(
        help_text="Email or Phone Number"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate login credentials"""
        identifier = attrs.get('identifier')
        password = attrs.get('password')
        
        if not identifier or not password:
            raise serializers.ValidationError("Both identifier and password are required")
        
        # Try to find user by email or phone
        user = None
        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(phone_number=identifier).first()
        
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")
        
        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError("Account is not activated. Please verify your email/phone.")
        
        attrs['user'] = user
        return attrs


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    
    identifier = serializers.CharField(
        help_text="Email or Phone Number"
    )
    otp_code = serializers.CharField(
        min_length=4,
        max_length=6
    )
    otp_type = serializers.ChoiceField(
        choices=OTPVerification.OTP_TYPES
    )
    
    def validate(self, attrs):
        """Validate OTP"""
        identifier = attrs.get('identifier')
        otp_code = attrs.get('otp_code')
        otp_type = attrs.get('otp_type')
        
        # Find user by identifier
        user = None
        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(phone_number=identifier).first()
        
        if not user:
            raise serializers.ValidationError("User not found")
        
        # Find active OTP
        otp_verification = OTPVerification.objects.filter(
            user=user,
            recipient=identifier,
            otp_type=otp_type,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_verification:
            raise serializers.ValidationError("No active OTP found")
        
        if not otp_verification.can_attempt():
            raise serializers.ValidationError("OTP has expired or exceeded maximum attempts")
        
        attrs['user'] = user
        attrs['otp_verification'] = otp_verification
        return attrs


class OTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting OTP"""
    
    identifier = serializers.CharField(
        help_text="Email or Phone Number"
    )
    otp_type = serializers.ChoiceField(
        choices=OTPVerification.OTP_TYPES
    )
    
    def validate(self, attrs):
        """Validate OTP request"""
        identifier = attrs.get('identifier')
        otp_type = attrs.get('otp_type')
        
        # Find user by identifier
        user = None
        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(phone_number=identifier).first()
        
        if not user:
            raise serializers.ValidationError("User not found")
        
        attrs['user'] = user
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    identifier = serializers.CharField(
        help_text="Email or Phone Number"
    )
    
    def validate_identifier(self, value):
        """Validate identifier and check if user exists"""
        user = None
        if '@' in value:
            user = User.objects.filter(email=value).first()
        else:
            user = User.objects.filter(phone_number=value).first()
        
        if not user:
            raise serializers.ValidationError("User with this identifier not found")
        
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    identifier = serializers.CharField(
        help_text="Email or Phone Number"
    )
    otp_code = serializers.CharField(
        min_length=4,
        max_length=6
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password reset confirmation"""
        identifier = attrs.get('identifier')
        otp_code = attrs.get('otp_code')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # Check if passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        
        # Find user by identifier
        user = None
        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(phone_number=identifier).first()
        
        if not user:
            raise serializers.ValidationError("User not found")
        
        # Find active password reset OTP
        otp_verification = OTPVerification.objects.filter(
            user=user,
            recipient=identifier,
            otp_type='password_reset',
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_verification:
            raise serializers.ValidationError("No active password reset OTP found")
        
        if not otp_verification.can_attempt():
            raise serializers.ValidationError("OTP has expired or exceeded maximum attempts")
        
        attrs['user'] = user
        attrs['otp_verification'] = otp_verification
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = User
        fields = (
            'uuid', 'email', 'phone_number', 'full_name',
            'email_verified', 'phone_verified', 'is_active',
            'date_joined', 'updated_at'
        )
        read_only_fields = (
            'uuid', 'email_verified', 'phone_verified', 'is_active',
            'date_joined', 'updated_at'
        )


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ('full_name', 'email', 'phone_number')
        
    def validate_email(self, value):
        """Validate email uniqueness"""
        if value and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number uniqueness and format"""
        if value:
            # Check uniqueness
            if User.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("User with this phone number already exists")
            
            # Check format
            phone_regex = r'^\+?1?\d{9,15}$'
            if not re.match(phone_regex, value):
                raise serializers.ValidationError("Invalid phone number format")
        
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password change"""
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # Check if passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError("New passwords do not match")
        
        # Check old password
        user = self.context['request'].user
        if not user.check_password(old_password):
            raise serializers.ValidationError("Invalid old password")
        
        return attrs