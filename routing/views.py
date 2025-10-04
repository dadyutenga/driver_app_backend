import logging
from typing import Any, Dict, List

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Ride
from .serializers import RideSerializer


logger = logging.getLogger(__name__)


ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/{profile}"
ORS_AUTOCOMPLETE_URL = "https://api.openrouteservice.org/geocode/autocomplete"
ORS_REVERSE_URL = "https://api.openrouteservice.org/geocode/reverse"
REQUEST_TIMEOUT = 10
DEFAULT_PROFILE = "driving-car"


def _get_ors_headers(include_content_type: bool = True) -> Dict[str, str]:
	api_key = getattr(settings, "OPENROUTESERVICE_API_KEY", "")
	if not api_key:
		raise ValueError("OPENROUTESERVICE_API_KEY is not configured in settings.")
	headers = {"Authorization": api_key}
	if include_content_type:
		headers["Content-Type"] = "application/json"
	return headers


@api_view(["GET"])
@permission_classes([AllowAny])
def routing_index(request):
	"""Health check endpoint so clients know the routing API is reachable."""
	return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def list_rides(request):
	rides = Ride.objects.order_by("-created_at")
	serializer = RideSerializer(rides, many=True)
	return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def autocomplete_places(request):
	query = request.query_params.get("q", "").strip()
	if not query:
		return Response(
			{"detail": "Missing required query parameter 'q'."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	size_param = request.query_params.get("size", "5")
	try:
		size = max(1, min(int(size_param), 10))
	except ValueError:
		return Response(
			{"detail": "Query parameter 'size' must be an integer."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	try:
		headers = _get_ors_headers(include_content_type=False)
	except ValueError as exc:
		return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	params = {"text": query, "size": size}
	try:
		ors_response = requests.get(
			ORS_AUTOCOMPLETE_URL,
			params=params,
			headers=headers,
			timeout=REQUEST_TIMEOUT,
		)
		ors_response.raise_for_status()
	except requests.RequestException as exc:
		logger.exception("OpenRouteService autocomplete request failed")
		return Response(
			{"detail": "Error querying autocomplete service.", "error": str(exc)},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	data = ors_response.json()
	features: List[Dict[str, Any]] = data.get("features", [])
	results: List[Dict[str, Any]] = []
	for feature in features:
		geometry = feature.get("geometry", {})
		coords = geometry.get("coordinates", [])
		properties = feature.get("properties", {})
		if len(coords) != 2:
			continue
		results.append(
			{
				"label": properties.get("label"),
				"locality": properties.get("locality"),
				"region": properties.get("region"),
				"country": properties.get("country"),
				"confidence": properties.get("confidence"),
				"lat": coords[1],
				"lng": coords[0],
			}
		)

	return Response({"results": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def reverse_geocode(request):
	lat = request.query_params.get("lat")
	lng = request.query_params.get("lng")
	if lat is None or lng is None:
		return Response(
			{"detail": "Query parameters 'lat' and 'lng' are required."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	try:
		lat_val = float(lat)
		lng_val = float(lng)
	except ValueError:
		return Response(
			{"detail": "Parameters 'lat' and 'lng' must be valid numbers."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	try:
		headers = _get_ors_headers(include_content_type=False)
	except ValueError as exc:
		return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	params = {"point.lat": lat_val, "point.lon": lng_val}
	try:
		ors_response = requests.get(
			ORS_REVERSE_URL,
			params=params,
			headers=headers,
			timeout=REQUEST_TIMEOUT,
		)
		ors_response.raise_for_status()
	except requests.RequestException as exc:
		logger.exception("OpenRouteService reverse geocode request failed")
		return Response(
			{"detail": "Error querying reverse geocode service.", "error": str(exc)},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	data = ors_response.json()
	features: List[Dict[str, Any]] = data.get("features", [])
	if not features:
		return Response({"detail": "No address found for the provided coordinates."}, status=status.HTTP_404_NOT_FOUND)

	top = features[0]
	properties = top.get("properties", {})
	return Response({
		"label": properties.get("label"),
		"locality": properties.get("locality"),
		"region": properties.get("region"),
		"country": properties.get("country"),
	})


@api_view(["POST"])
@permission_classes([AllowAny])
def create_ride(request):
	data = request.data
	try:
		start_lat = float(data["start_lat"])
		start_lng = float(data["start_lng"])
		end_lat = float(data["end_lat"])
		end_lng = float(data["end_lng"])
	except (KeyError, TypeError, ValueError):
		return Response(
			{"detail": "Missing or invalid coordinates. Provide start_lat, start_lng, end_lat, and end_lng."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	driver_raw = data.get("driver_id")
	try:
		driver_id = int(driver_raw) if driver_raw not in (None, "") else None
	except (TypeError, ValueError):
		return Response(
			{"detail": "driver_id must be an integer if provided."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	profile = data.get("profile", DEFAULT_PROFILE)
	ors_payload = {"coordinates": [[start_lng, start_lat], [end_lng, end_lat]]}

	try:
		headers = _get_ors_headers()
	except ValueError as exc:
		return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

	try:
		ors_response = requests.post(
			ORS_DIRECTIONS_URL.format(profile=profile),
			json=ors_payload,
			headers=headers,
			timeout=REQUEST_TIMEOUT,
		)
		ors_response.raise_for_status()
	except requests.RequestException as exc:
		logger.exception("OpenRouteService directions request failed")
		return Response(
			{"detail": "Error fetching route from OpenRouteService.", "error": str(exc)},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	ors_data = ors_response.json()
	try:
		route = ors_data["routes"][0]
	except (KeyError, IndexError):
		return Response(
			{"detail": "Invalid response from OpenRouteService."},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	summary = route.get("summary", {})
	distance_m = summary.get("distance", 0)
	duration_s = summary.get("duration", 0)
	geometry = route.get("geometry")
	if geometry is None:
		return Response(
			{"detail": "Route geometry missing from OpenRouteService response."},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	distance_km = round(distance_m / 1000.0, 3)
	duration_min = round(duration_s / 60.0, 2)

	ride = Ride.objects.create(
		driver_id=driver_id,
		start_lat=start_lat,
		start_lng=start_lng,
		start_address=data.get("start_address", ""),
		end_lat=end_lat,
		end_lng=end_lng,
		end_address=data.get("end_address", ""),
		distance_km=distance_km,
		duration_min=duration_min,
		geometry=geometry,
	)

	serializer = RideSerializer(ride)
	return Response(serializer.data, status=status.HTTP_201_CREATED)