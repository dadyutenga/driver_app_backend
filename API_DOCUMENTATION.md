# Driver App Backend API Documentation

## Overview
This is a comprehensive Django REST API for a driver sharing application with advanced authentication features including:
- Email/Phone authentication
- OTP verification (4-digit codes)
- JWT tokens
- OAuth integration (Google, Facebook)
- SMS (Twilio, AfricasTalking) and Email support

## Base URL
```
http://localhost:8000/api/v1/
```

## Authentication Endpoints

### 1. User Registration
**POST** `/auth/register/`

Register a new user with email or phone number.

**Request Body:**
```json
{
    "email": "user@example.com",           // Optional if phone_number provided
    "phone_number": "+1234567890",        // Optional if email provided  
    "full_name": "John Doe",
    "password": "secure_password123",
    "confirm_password": "secure_password123"
}
```

**Response:**
```json
{
    "success": true,
    "message": "User registered successfully. Please verify your account.",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "phone_number": "+1234567890",
        "full_name": "John Doe",
        "email_verified": false,
        "phone_verified": false,
        "is_active": false,
        "date_joined": "2025-09-24T10:00:00Z"
    },
    "otp_sent": true,
    "otp_message": "OTP sent successfully",
    "verification_required": true
}
```

### 2. User Login
**POST** `/auth/login/`

Login with email/phone and password.

**Request Body:**
```json
{
    "identifier": "user@example.com",     // Email or phone number
    "password": "secure_password123"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Login successful",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "is_active": true
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

### 3. OTP Verification
**POST** `/auth/verify-otp/`

Verify OTP code sent via SMS or email.

**Request Body:**
```json
{
    "identifier": "user@example.com",     // Email or phone number
    "otp_code": "1234",                   // 4-digit OTP
    "otp_type": "email"                   // email, phone, login, password_reset
}
```

**Response:**
```json
{
    "success": true,
    "message": "OTP verified successfully",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "is_active": true,
        "email_verified": true
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

### 4. Resend OTP
**POST** `/auth/resend-otp/`

Request a new OTP code.

**Request Body:**
```json
{
    "identifier": "user@example.com",
    "otp_type": "email"
}
```

### 5. Password Reset Request
**POST** `/auth/password-reset/`

Request password reset OTP.

**Request Body:**
```json
{
    "identifier": "user@example.com"
}
```

### 6. Password Reset Confirm
**POST** `/auth/password-reset/confirm/`

Reset password with OTP verification.

**Request Body:**
```json
{
    "identifier": "user@example.com",
    "otp_code": "1234",
    "new_password": "new_secure_password123",
    "confirm_password": "new_secure_password123"
}
```

### 7. User Logout
**POST** `/auth/logout/`

Logout and blacklist refresh token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## Profile Management

### 8. Get/Update Profile
**GET/PUT/PATCH** `/auth/profile/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**PUT Request Body:**
```json
{
    "full_name": "John Updated",
    "email": "newemail@example.com",
    "phone_number": "+1987654321"
}
```

### 9. Change Password
**POST** `/auth/change-password/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
    "old_password": "current_password",
    "new_password": "new_secure_password123",
    "confirm_password": "new_secure_password123"
}
```

## OAuth Integration

### 10. Google OAuth
**POST** `/auth/oauth/google/`

Authenticate with Google OAuth token.

**Request Body:**
```json
{
    "access_token": "google_access_token_here"
}
```

### 11. Facebook OAuth
**POST** `/auth/oauth/facebook/`

Authenticate with Facebook OAuth token.

**Request Body:**
```json
{
    "access_token": "facebook_access_token_here"
}
```

### 12. OAuth Applications
**GET** `/auth/oauth/applications/`

Get available OAuth applications and endpoints.

## Session Management

### 13. User Sessions
**GET** `/auth/sessions/`

Get all active user sessions.

**Headers:**
```
Authorization: Bearer <access_token>
```

### 14. Terminate Session
**POST** `/auth/sessions/<session_id>/terminate/`

Terminate a specific session.

**Headers:**
```
Authorization: Bearer <access_token>
```

## JWT Token Management

### 15. Refresh Token
**POST** `/auth/token/refresh/`

Get new access token using refresh token.

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "success": false,
    "message": "Error description",
    "errors": {
        "field_name": ["Error details"]
    }
}
```

## Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting
- OTP requests: 1 per minute per user
- Login attempts: 5 per minute per IP
- Registration: 3 per hour per IP

## Configuration

### Environment Variables
Create `.env` file with:

```env
# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# AfricasTalking Configuration
AFRICASTALKING_USERNAME=your-africastalking-username
AFRICASTALKING_API_KEY=your-africastalking-api-key
AFRICASTALKING_SENDER_ID=your-sender-id
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create OAuth applications:
```bash
python manage.py setup_oauth
```

4. Create superuser:
```bash
python manage.py createsuperuser
```

5. Start server:
```bash
python manage.py runserver
```

6. Start Celery worker (for background tasks):
```bash
celery -A driver_app_backend worker -l info
```

## Testing

Use tools like Postman or curl to test the endpoints:

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "testpass123",
    "confirm_password": "testpass123"
  }'

# Verify OTP
curl -X POST http://localhost:8000/api/v1/auth/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "otp_code": "1234",
    "otp_type": "email"
  }'
```