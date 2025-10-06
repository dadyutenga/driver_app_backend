from django.urls import path

from . import views

app_name = 'data'

urlpatterns = [
    path('driver/verification/', views.driver_verification, name='driver-verification'),
    path('driver/profile/', views.get_driver_profile, name='driver-profile'),
    path('driver/car/', views.get_car_details, name='driver-car'),
]