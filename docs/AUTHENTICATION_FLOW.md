# Driver App Backend - Authentication Flow Documentation

## Overview

Your authentication system implements a **Registration → OTP Verification → Authentication** flow as requested. Here's how it works:

## 🔐 Authentication Flow

### 1. **User Registration**
```http
POST /api/v1/auth/register/
Content-Type: application/json

{
    "email": "user@example.com",
    "phone_number": "+1234567890",  // Optional
    "full_name": "John Doe",
    "password": "securepassword123",
    "confirm_password": "securepassword123"
}
```

**Response:**
```json
{
    "success": true,
    "message": "User registered successfully. Please verify your account.",
    "user": {
        "id": "uuid-here",
        "email": "user@example.com",
        "phone_number": "+1234567890",
        "full_name": "John Doe",
        "email_verified": false,
        "phone_verified": false,
        "is_active": false
    },
    "otp_sent": true,
    "otp_message": "OTP sent successfully",
    "verification_required": true
}
```

### 2. **OTP Verification (After Registration)**
```http
POST /api/v1/auth/verify-otp/
Content-Type: application/json

{
    "identifier": "user@example.com",
    "otp_code": "1234",
    "otp_type": "email"
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "OTP verified successfully",
    "user": {
        "id": "uuid-here",
        "email": "user@example.com",
        "full_name": "John Doe",
        "email_verified": true,
        "is_active": true
    },
    "tokens": {
        "access": "jwt-access-token",
        "refresh": "jwt-refresh-token"
    }
}
```

### 3. **User Login (For Returning Users)**
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
    "identifier": "user@example.com",  // Email or phone
    "password": "securepassword123"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "id": "uuid-here",
        "email": "user@example.com",
        "full_name": "John Doe",
        "email_verified": true,
        "is_active": true
    },
    "tokens": {
        "access": "jwt-access-token",
        "refresh": "jwt-refresh-token"
    }
}
```

## 🔄 Additional Authentication Features

### **Resend OTP**
```http
POST /api/v1/auth/request-otp/
Content-Type: application/json

{
    "identifier": "user@example.com",
    "otp_type": "email"
}
```

### **Password Reset Flow**

1. **Request Password Reset:**
```http
POST /api/v1/auth/password-reset/
Content-Type: application/json

{
    "identifier": "user@example.com"
}
```

2. **Confirm Password Reset with OTP:**
```http
POST /api/v1/auth/password-reset/confirm/
Content-Type: application/json

{
    "identifier": "user@example.com",
    "otp_code": "1234",
    "new_password": "newpassword123",
    "confirm_password": "newpassword123"
}
```

### **OAuth Authentication**

**Google OAuth:**
```http
POST /api/v1/auth/oauth/google/
Content-Type: application/json

{
    "access_token": "google-oauth-access-token"
}
```

**Facebook OAuth:**
```http
POST /api/v1/auth/oauth/facebook/
Content-Type: application/json

{
    "access_token": "facebook-oauth-access-token"
}
```

## 🛡️ Security Features

### **Token Management**
- **JWT Tokens**: Access tokens (60 min) and refresh tokens (7 days)
- **Token Blacklisting**: Proper logout with token invalidation
- **Token Rotation**: Refresh tokens rotate on use

### **Rate Limiting**
- **OTP Requests**: Limited to prevent abuse
- **Failed Attempts**: Account lockout after multiple failures
- **Session Management**: Track user sessions and device info

### **Verification System**
- **Email Verification**: Required for email-based registration
- **Phone Verification**: Required for phone-based registration
- **OTP Expiry**: Configurable (default 10 minutes)
- **Attempt Limits**: Maximum 3 attempts per OTP

## 🔧 Configuration

### **OTP Settings (in settings.py):**
```python
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 4
OTP_MAX_ATTEMPTS = 3
```

### **JWT Settings:**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### **Email Configuration:**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### **SMS Configuration:**
```python
# Twilio Configuration
TWILIO_ACCOUNT_SID = 'your-twilio-account-sid'
TWILIO_AUTH_TOKEN = 'your-twilio-auth-token'
TWILIO_PHONE_NUMBER = 'your-twilio-phone-number'

# AfricasTalking Configuration
AFRICASTALKING_USERNAME = 'your-africastalking-username'
AFRICASTALKING_API_KEY = 'your-africastalking-api-key'
AFRICASTALKING_SENDER_ID = 'your-sender-id'
```

## 📱 Frontend Integration

### **Protected Routes**
Use the access token in the Authorization header:
```javascript
headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
}
```

### **Token Refresh**
```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "jwt-refresh-token"
}
```

## 🐛 Fixes Applied

✅ **pkg_resources warnings removed** - Added warning filters to suppress deprecated API warnings
✅ **Token blacklisting enabled** - Added `rest_framework_simplejwt.token_blacklist` to INSTALLED_APPS
✅ **Database migrations applied** - All token blacklist migrations completed
✅ **Authentication flow verified** - Registration → OTP → Authentication flow working

## 🚀 Ready to Use

Your authentication system is now fully functional with:
- ✅ User registration with OTP verification
- ✅ Login with JWT token generation  
- ✅ Password reset with OTP verification
- ✅ OAuth integration (Google/Facebook)
- ✅ Session management
- ✅ Security features and rate limiting
- ✅ No more pkg_resources warnings

The server should now start clean without any deprecated API warnings!