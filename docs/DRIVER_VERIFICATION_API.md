# Driver Verification API Documentation

## Overview
This document outlines the API endpoints for submitting and retrieving driver verification data, including personal information, vehicle details, and required photo uploads.

## Endpoints

### Submit Driver Verification
```
POST /api/v1/data/driver/verification
```

### Get Driver Profile
```
GET /api/v1/data/driver/profile
```

### Get Car Details
```
GET /api/v1/data/driver/car
```

## Request Format
The request must be sent as `multipart/form-data` to handle both form fields and file uploads.

## Request Parameters

### Form Fields

#### Personal Information
| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `fullName` | string | Yes | Driver's full legal name |
| `nidaNumber` | string | Yes | National ID number |
| `address` | string | Yes | Driver's complete residential address |

#### Vehicle Information
| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `carName` | string | Yes | Vehicle make and model (e.g., "Toyota Corolla 2020") |
| `plateNumber` | string | Yes | Vehicle license plate number (e.g., "T123ABC") |
| `carType` | string | Yes | Type of vehicle. Allowed values: `Sedan`, `SUV`, `Pickup`, `Van`, `Coupe` |
| `numberOfSeats` | integer | Yes | Number of passenger seats. Allowed values: 2, 3, 4, 5, 6, 7 |

### File Uploads
| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `profilePhoto` | file | Yes | Driver's profile photo (JPEG/PNG, max 5MB) |
| `idPhoto` | file | Yes | Photo of driver's ID document (JPEG/PNG, max 5MB) |
| `carPhoto` | file | Yes | Photo of the vehicle (JPEG/PNG, max 5MB) |

## Validation Rules

### Personal Information
- `fullName`: Must not be empty, minimum 2 characters, maximum 100 characters
- `nidaNumber`: Must be a valid NIDA number format (implementation-specific validation)
- `address`: Must not be empty, minimum 10 characters, maximum 500 characters

### Vehicle Information
- `carName`: Must not be empty, minimum 3 characters, maximum 100 characters
- `plateNumber`: Must match the country's license plate format (e.g., regex validation)
- `carType`: Must be one of the predefined values
- `numberOfSeats`: Must be an integer between 2 and 7 inclusive

### File Uploads
- All three photos are mandatory
- Supported formats: JPEG, PNG
- Maximum file size: 5MB per file
- Minimum resolution: 300x300 pixels
- Images should be clear and properly oriented

## Request Example

```bash
curl -X POST \
  http://api.example.com/api/driver/verification \
  -F "fullName=John Doe" \
  -F "nidaNumber=1234567890123456" \
  -F "address=123 Main Street, City, Country" \
  -F "carName=Toyota Corolla 2020" \
  -F "plateNumber=T123ABC" \
  -F "carType=Sedan" \
  -F "numberOfSeats=4" \
  -F "profilePhoto=@profile.jpg" \
  -F "idPhoto=@id_card.jpg" \
  -F "carPhoto=@car.jpg"
```

## Response Format

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "Driver verification submitted successfully",
  "data": {
    "verificationId": "ver_123456789",
    "status": "pending",
    "submittedAt": "2025-10-06T10:30:00Z"
  }
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {
      "field": "fullName",
      "message": "Full name is required"
    },
    {
      "field": "profilePhoto",
      "message": "Profile photo is required and must be a valid image file"
    }
  ]
}
```

### Error Response (500 Internal Server Error)
```json
{
  "success": false,
  "message": "Internal server error occurred while processing verification"
}
```

## Status Codes
- `200`: Verification submitted successfully
- `400`: Validation error or missing required fields
- `401`: Unauthorized (invalid API key or authentication)
- `413`: File too large
- `415`: Unsupported file format
- `500`: Internal server error

## Notes
- All file uploads should be compressed appropriately to reduce bandwidth usage
- The API should implement rate limiting to prevent abuse
- Consider implementing image processing to validate and optimize uploaded photos
- Store files securely with appropriate access controls
- Implement proper logging for audit trails
- Consider adding image compression on the server side to save storage space

## Get Driver Profile

### Endpoint
```
GET /api/v1/data/driver/profile
```

### Authentication
Requires JWT authentication.

### Response Format

#### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "fullName": "John Doe",
    "profilePhoto": "https://api.example.com/media/profile_photos/john_doe.jpg"
  }
}
```

#### Error Response (404 Not Found)
```json
{
  "success": false,
  "message": "Driver profile not found."
}
```

## Get Car Details

### Endpoint
```
GET /api/v1/data/driver/car
```

### Authentication
Requires JWT authentication.

### Response Format

#### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "carName": "Toyota Corolla 2020",
    "plateNumber": "T123ABC",
    "carType": "Sedan",
    "numberOfSeats": 4,
    "carPhoto": "https://api.example.com/media/car_photos/toyota_corolla.jpg"
  }
}
```

#### Error Response (404 Not Found)
```json
{
  "success": false,
  "message": "Driver profile not found."
}
```</content>
<parameter name="filePath">d:\projects\ride_driver\DRIVER_VERIFICATION_API.md