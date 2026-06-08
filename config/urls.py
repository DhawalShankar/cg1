# config/urls.py
from django.urls import path, include

urlpatterns = [
    path("api/", include("apps.bookings.urls")),
    path("api/notifications/", include("apps.notifications.urls")),  # ← add this
]