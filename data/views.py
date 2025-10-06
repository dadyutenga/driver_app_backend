from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Driver
from .serializers import DriverVerificationSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def driver_verification(request):
    """
    Submit driver verification data including personal info, vehicle details, and photos.
    """
    if hasattr(request.user, 'driver_profile') and request.user.driver_profile:
        return Response(
            {"success": False, "message": "Driver verification already submitted."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = DriverVerificationSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        driver = serializer.save()
        return Response({
            "success": True,
            "message": "Driver verification submitted successfully",
            "data": {
                "verificationId": str(driver.id),
                "status": driver.status,
                "submittedAt": driver.submitted_at.isoformat()
            }
        }, status=status.HTTP_201_CREATED)
    else:
        errors = []
        for field, messages in serializer.errors.items():
            for message in messages:
                errors.append({"field": field, "message": message})
        return Response(
            {"success": False, "message": "Validation failed", "errors": errors},
            status=status.HTTP_400_BAD_REQUEST
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_profile(request):
    """
    Retrieve the driver's profile photo and full name.
    """
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {"success": False, "message": "Driver profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    profile_photo_url = driver.profile_photo.url if driver.profile_photo else None

    return Response({
        "success": True,
        "data": {
            "fullName": driver.full_name,
            "profilePhoto": profile_photo_url
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_car_details(request):
    """
    Retrieve the driver's car details.
    """
    try:
        driver = request.user.driver_profile
    except Driver.DoesNotExist:
        return Response(
            {"success": False, "message": "Driver profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        "success": True,
        "data": {
            "carName": driver.car_name,
            "plateNumber": driver.plate_number,
            "carType": driver.car_type,
            "numberOfSeats": driver.number_of_seats,
            "carPhoto": driver.car_photo.url if driver.car_photo else None
        }
    })
