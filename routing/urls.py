from django.urls import path

from . import views


app_name = "routing"


urlpatterns = [
    path("", views.routing_index, name="index"),
    path("rides/", views.list_rides, name="ride-list"),
    path("rides/create/", views.create_ride, name="ride-create"),
    path("places/autocomplete/", views.autocomplete_places, name="places-autocomplete"),
    path("places/reverse/", views.reverse_geocode, name="places-reverse"),
]