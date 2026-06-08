import uuid
from django.db import models

class Notification(models.Model):
    TYPE_CHOICES = [
        ("booking", "Booking"),
        ("payment", "Payment"),
        ("message", "Message"),
        ("system",  "System"),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id    = models.CharField(max_length=255, db_index=True)  # Clerk user ID
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    url        = models.CharField(max_length=500, null=True, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]