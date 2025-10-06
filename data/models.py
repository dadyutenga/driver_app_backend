from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

from authentication.models import User


class Driver(models.Model):
    CAR_TYPES = [
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Pickup', 'Pickup'),
        ('Van', 'Van'),
        ('Coupe', 'Coupe'),
    ]

    SEAT_CHOICES = [
        (2, '2 seats'),
        (3, '3 seats'),
        (4, '4 seats'),
        (5, '5 seats'),
        (6, '6 seats'),
        (7, '7 seats'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    full_name = models.CharField(max_length=100)
    nida_number = models.CharField(max_length=20, unique=True)
    address = models.TextField()

    car_name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=20, unique=True)
    car_type = models.CharField(max_length=10, choices=CAR_TYPES)
    number_of_seats = models.IntegerField(choices=SEAT_CHOICES, validators=[MinValueValidator(2), MaxValueValidator(7)])

    profile_photo = models.ImageField(upload_to='drivers/photos/', blank=True, null=True)
    id_photo = models.ImageField(upload_to='drivers/ids/', blank=True, null=True)
    car_photo = models.ImageField(upload_to='drivers/cars/', blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'data_driver'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Driver {self.full_name} ({self.user})"
