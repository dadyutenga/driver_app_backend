# Routing API Documentation

## Overview
The routing module exposes location-aware endpoints backed by OpenRouteService. It provides autocomplete search, reverse geocoding, and turn-by-turn routing so that clients can create and store `Ride` records with distance, duration, and geometry data.

- API base path: `http://localhost:8000/api/v1/routing/`
- Authentication: **not required** for initial testing (all endpoints use `AllowAny`).
- Response format: JSON
- Geographic scope: **Tanzania only**. Requests using coordinates or results outside the national bounds are rejected.

## Prerequisites
1. Ensure the Django server is running: `python manage.py runserver`
2. Configure an OpenRouteService API key in `.env`:
   ```env
   OPENROUTESERVICE_API_KEY=your-openrouteservice-api-key
   ```
3. Apply migrations so the `Ride` table exists:
   ```bash
   python manage.py makemigrations routing
   python manage.py migrate
   ```

## Endpoints at a Glance
- `GET /` – Service health check
- `GET /rides/` – List stored rides
- `POST /rides/create/` – Create a ride from coordinates
- `GET /places/autocomplete/` – Location suggestions
- `GET /places/reverse/` – Reverse geocoding

## Endpoint Details

### 1. Service Health Check
**GET** `/`

Returns a simple payload so clients can verify that the routing service is reachable.

**Response 200**
```json
{
    "status": "ok"
}
```

### 2. List Rides
**GET** `/rides/`

Retrieves rides ordered from newest to oldest.

**Response 200**
```json
[
    {
        "id": 1,
        "driver_id": 42,
        "start_lat": -6.7924,
        "start_lng": 39.2083,
        "start_address": "Dar es Salaam, Tanzania",
        "end_lat": -6.1659,
        "end_lng": 39.2026,
        "end_address": "Zanzibar, Tanzania",
        "distance_km": 80.553,
        "duration_min": 92.5,
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [39.2083, -6.7924],
                [39.2026, -6.1659]
            ]
        },
        "created_at": "2025-10-04T13:02:10.991Z"
    }
]
```

### 3. Create Ride
**POST** `/rides/create/`

Requests directions from OpenRouteService and stores the resulting ride. Both the origin and destination must be within Tanzania.

**Request Body**
```json
{
    "start_lat": -6.7924,
    "start_lng": 39.2083,
    "end_lat": -6.1659,
    "end_lng": 39.2026,
    "start_address": "Dar es Salaam",
    "end_address": "Zanzibar",
    "driver_id": 42,
    "profile": "driving-car"
}
```

- `driver_id`, `start_address`, and `end_address` are optional.
- `profile` defaults to `driving-car`. Other supported OpenRouteService profiles (for example `cycling-regular`, `foot-walking`) can be supplied.

**Response 201**
```json
{
    "id": 2,
    "driver_id": 42,
    "start_lat": -6.7924,
    "start_lng": 39.2083,
    "start_address": "Dar es Salaam",
    "end_lat": -6.1659,
    "end_lng": 39.2026,
    "end_address": "Zanzibar",
    "distance_km": 80.553,
    "duration_min": 92.5,
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [39.2083, -6.7924],
            [39.2026, -6.1659]
        ]
    },
    "created_at": "2025-10-04T13:10:31.441Z"
}
```

### 4. Place Autocomplete
**GET** `/places/autocomplete/?q=<query>&size=<1-10>`

Wraps OpenRouteService autocomplete to provide forward geocoding suggestions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q`       | string | Yes | Search text (e.g. `dar es salaam`). |
| `size`    | int | No | Limits results (default 5, max 10). |

**Response 200**
```json
{
    "results": [
        {
            "label": "Kilimanjaro International Airport, Tanzania",
            "locality": "Hai",
            "region": "Kilimanjaro",
            "country": "Tanzania",
            "confidence": 0.9,
            "lat": -3.429586,
            "lng": 37.074467
        }
    ]
}
```

### 5. Reverse Geocode
**GET** `/places/reverse/?lat=<latitude>&lng=<longitude>`

Returns the best matching address for the supplied coordinates. The supplied coordinates must lie within Tanzania.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat`     | float | Yes | Latitude value. |
| `lng`     | float | Yes | Longitude value. |

**Response 200**
```json
{
    "label": "Zanzibar Port, Zanzibar, Tanzania",
    "locality": "Zanzibar",
    "region": "Mjini Magharibi",
    "country": "Tanzania"
}
```

## Error Handling
All routing endpoints return errors in a consistent structure:

```json
{
    "detail": "Error message",
    "error": "Optional extra details"
}
```

Common cases:
- `400 Bad Request` – Missing or invalid parameters, or coordinates outside Tanzania.
- `404 Not Found` – No Tanzanian matches for the provided query or coordinates.
- `502 Bad Gateway` – Issues communicating with OpenRouteService (network errors, invalid profile, rate limiting).
- `500 Internal Server Error` – Server misconfiguration such as a missing API key.

## Quick Test Commands
Use the following curl snippets (PowerShell compatible) to exercise the API once the server is running.

```powershell
# Health check
curl "http://localhost:8000/api/v1/routing/"

# Autocomplete
curl "http://localhost:8000/api/v1/routing/places/autocomplete/?q=dar%20es%20salaam"

# Reverse geocode
curl "http://localhost:8000/api/v1/routing/places/reverse/?lat=-6.7924&lng=39.2083"

# Create ride
curl -Method POST "http://localhost:8000/api/v1/routing/rides/create/" ^
  -ContentType "application/json" ^
  -Body '{
    "start_lat": -6.7924,
    "start_lng": 39.2083,
    "end_lat": -6.1659,
    "end_lng": 39.2026
  }'
```

## Data Model Snapshot
The `Ride` model stores the following fields:

| Field | Type | Notes |
|-------|------|-------|
| `driver_id` | integer | Optional driver reference. |
| `start_lat` / `start_lng` | float | Origin coordinates. |
| `start_address` | string | Optional origin label. |
| `end_lat` / `end_lng` | float | Destination coordinates. |
| `end_address` | string | Optional destination label. |
| `distance_km` | float | Route length in kilometers. |
| `duration_min` | float | Travel time in minutes. |
| `geometry` | JSON | GeoJSON geometry returned by OpenRouteService. |
| `created_at` | datetime | Timestamp of creation. |

Use this document alongside `API_DOCUMENTATION.md` for full backend coverage.
