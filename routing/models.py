from django.db import models

from data.models import Driver


class Ride(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    start_lat = models.FloatField()
    start_lng = models.FloatField()
    start_address = models.CharField(max_length=255, blank=True)
    end_lat = models.FloatField()
    end_lng = models.FloatField()
    end_address = models.CharField(max_length=255, blank=True)
    distance_km = models.FloatField()
    duration_min = models.FloatField()
    geometry = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Ride {self.id} from ({self.start_lat}, {self.start_lng}) "
            f"to ({self.end_lat}, {self.end_lng})"
        )