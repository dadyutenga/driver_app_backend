from django.urls import path
from . import views

app_name = 'routing'

urlpatterns = [
    # Routing endpoints will be added here
    # For now, we'll add a placeholder
    path('', views.routing_index, name='index'),
]