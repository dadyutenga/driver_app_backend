# Driver App Backend API Documentation

## Overview
This is a comprehensive Django REST API for a driver sharing application with advanced authentication features including:
- Email/Phone authentication
- OTP verification (4-digit codes)
- JWT tokens
- OAuth integration (Google, Facebook)
- SMS (Twilio, AfricasTalking) and Email support

Routing-specific endpoints are documented separately in `ROUTING_API.md`.

Driver verification endpoints are documented separately in `DRIVER_VERIFICATION_API.md`.

## Base URL
```
http://localhost:8000/api/v1/
```

## Authentication Endpoints

### 1. User Registration (Step 1 of 2)
**POST** `/auth/register/`

Registers a new user and immediately issues a 2FA OTP challenge (no tokens yet). User is active but must verify channel before receiving JWT tokens.

OTP Characteristics:

- Length: 4 characters
- Charset: 0-9 and A-Z (alphanumeric uppercase)
- Validity: `OTP_EXPIRY_MINUTES` (default 10 minutes)
- Delivery: Email if provided, otherwise phone (SMS). If email send fails it is retried up to 3 times with exponential backoff.

**Request Body:**

```json
{
    "email": "user@example.com",      // Optional if phone_number provided
    "phone_number": "+1234567890",   // Optional if email provided
    "full_name": "John Doe",
    "password": "secure_password123",
    "confirm_password": "secure_password123"
}
```

**Success Response (201):** (Trimmed)

```json
{
    "success": true,
    "message": "User registered. Enter the OTP sent to your contact."
}
```

Proceed to OTP Verification (Section 3) to obtain tokens.

### 2. User Login (Step 1 of 2)
 
**POST** `/auth/login/`

Authenticates password and triggers an OTP challenge (no tokens yet). Always requires OTP as second factor.

**Request Body:**

```json
{
    "identifier": "user@example.com",  // Email or phone number
    "password": "secure_password123"
}
```

**Success Response (200):** (Trimmed)

```json
{
    "success": true,
    "message": "Password accepted. Enter the OTP sent to your contact."
}
```

Proceed to OTP Verification (Section 3) to obtain tokens.

### 3. OTP Verification (Step 2 for Registration & Login)
 
**POST** `/auth/verify-otp/`

Verifies the OTP and returns JWT tokens (7‑day access, 30‑day refresh). For registration this also marks email/phone as verified. For login `otp_type` should be `login`.

Supported `otp_type` values: `email`, `phone`, `login`, `password_reset`.

**Request Body:**

```json
{
    "identifier": "user@example.com",  // Email or phone number used originally
    "otp_code": "A9K3",                // 4-char alphanumeric OTP (case-insensitive recommended client-side)
    "otp_type": "login"                // or email/phone/password_reset
}
```

**Success Response (200):** (Trimmed)

```json
{
    "success": true,
    "message": "OTP verified successfully",
    "user": {
        "uuid": "a3f0b4c2-...",
        "full_name": "John Doe",
        "email": "user@example.com"
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

### 4. Resend OTP
 
**POST** `/auth/resend-otp/`

Requests a new OTP (rate-limited: at most one per minute per identifier per type). Previous unverified OTPs are invalidated.

**Request Body:**

```json
{
    "identifier": "user@example.com",
    "otp_type": "login"   // or email / phone / password_reset
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

Logs out current session and (optionally) blacklists provided refresh token.

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

```text
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

```text
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

```text
Authorization: Bearer <access_token>
```

### 14. Terminate Session

**POST** `/auth/sessions/<session_id>/terminate/`

Terminate a specific session.

**Headers:**

```text
Authorization: Bearer <access_token>
```

## JWT Token Management

### 15. Refresh Token

**POST** `/auth/token/refresh/`

Obtain new access token using refresh token. Access lifetime: 7 days. Refresh lifetime: 30 days. Rotation enabled; previous refresh token is blacklisted upon use.

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

## Rate Limiting (Key Defaults)

- OTP resend: 1 per minute per identifier+type
- Background send retry: up to 3 attempts (1s, 2s, 4s delays)
- (Additional rate limits may exist at view or cache layer for login / brute force protection.)

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

# Routing (OpenRouteService)
OPENROUTESERVICE_API_KEY=your-openrouteservice-api-key
```

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

1. Create OAuth applications:

```bash
python manage.py setup_oauth
```

1. Create superuser:

```bash
python manage.py createsuperuser
```

1. Start server:

```bash
python manage.py runserver
```

1. Start Celery worker (for background tasks):

```bash
celery -A driver_app_backend worker -l info
```

## Testing

Use tools like Postman or curl to test the endpoints (new flow example with trimmed responses):

```bash
"# Register (Step 1)" \
curl -X POST http://localhost:8000/api/v1/auth/register/ \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpass123",
        "confirm_password": "testpass123"
    }'

"# Login (Step 1)" \
curl -X POST http://localhost:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{
        "identifier": "test@example.com",
        "password": "testpass123"
    }'

"# Verify OTP (Step 2 for either register or login)" \
curl -X POST http://localhost:8000/api/v1/auth/verify-otp/ \
    -H "Content-Type: application/json" \
    -d '{
        "identifier": "test@example.com",
        "otp_code": "A9K3",
        "otp_type": "login"
        }'

```