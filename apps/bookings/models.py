import uuid
from django.db import models

class BookingRequest(models.Model):
    STATUS = [
        ("pending",  "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("paid",     "Paid"),
    ]
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator_id      = models.UUIDField()
    requester_phone = models.CharField(max_length=15)
    occasion_type   = models.CharField(max_length=100, null=True, blank=True)
    event_date      = models.DateField()
    location        = models.CharField(max_length=255, null=True, blank=True)
    budget          = models.CharField(max_length=100, null=True, blank=True)
    note            = models.TextField(null=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS, default="pending")
    agreed_price    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    advance_percent = models.IntegerField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "booking_requests"
        managed  = False


class Payment(models.Model):
    STATUS = [
        ("created",  "Created"),
        ("captured", "Captured"),
        ("failed",   "Failed"),
    ]
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_request     = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name="payment")
    razorpay_order_id   = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature  = models.CharField(max_length=255, null=True, blank=True)
    amount_paise        = models.IntegerField()
    status              = models.CharField(max_length=20, choices=STATUS, default="created")
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"