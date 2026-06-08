import hmac
import hashlib
from decimal import Decimal
import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BookingRequest, Payment
from apps.notifications.models import Notification

rz = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _creator_user_id(creator_id: str) -> str | None:
    """BookingRequest.creator_id → Clerk user ID (profile_id) of that creator."""
    try:
        from apps.creators.models import Creator
        return str(Creator.objects.get(pk=creator_id).profile_id)
    except Exception:
        return None


class CreateBookingRequest(APIView):
    def post(self, request):
        creator_id      = request.data.get("creator_id")
        requester_id    = request.data.get("requester_id")
        requester_phone = request.data.get("requester_phone")
        occasion_type   = request.data.get("occasion_type")
        event_date      = request.data.get("event_date")
        location        = request.data.get("location")
        budget          = request.data.get("budget")
        note            = request.data.get("note")

        if not all([creator_id, requester_phone, event_date, location]):
            return Response({"error": "Missing required fields"}, status=400)

        # Block duplicate active requests
        existing = BookingRequest.objects.filter(
            creator_id      = creator_id,
            requester_phone = requester_phone,
            status__in      = ["pending", "accepted"],
        ).first()

        if existing:
            return Response({
                "id":     str(existing.id),
                "status": existing.status,
            }, status=200)

        br = BookingRequest.objects.create(
            creator_id      = creator_id,
            requester_id    = requester_id,
            requester_phone = requester_phone,
            occasion_type   = occasion_type,
            event_date      = event_date,
            location        = location,
            budget          = budget,
            note            = note,
            status          = "pending",
        )

        # Notify creator: new booking request received
        creator_user_id = _creator_user_id(str(creator_id))
        if creator_user_id:
            Notification.objects.create(
                user_id = creator_user_id,
                type    = "booking",
                title   = "New Booking Request! 📅",
                message = (
                    f"You have a new booking request for {occasion_type or 'an event'} "
                    f"on {event_date} in {location}."
                ),
                url = "/creator-dashboard",
            )

        return Response({"id": str(br.id), "status": br.status}, status=201)


class AcceptBookingRequest(APIView):
    def post(self, request, pk):
        try:
            br = BookingRequest.objects.get(pk=pk, status="pending")
        except BookingRequest.DoesNotExist:
            return Response({"error": "Not found or already handled"}, status=404)

        price   = request.data.get("agreed_price")
        advance = request.data.get("advance_percent", 50)

        if not price or int(price) <= 0:
            return Response({"error": "Invalid price"}, status=400)

        br.status          = "accepted"
        br.agreed_price    = Decimal(str(price))
        br.advance_percent = int(advance)
        br.save()

        # Notify requester: booking accepted with price
        if br.requester_id:
            advance_amt = int(br.agreed_price * br.advance_percent / 100)
            Notification.objects.create(
                user_id = br.requester_id,
                type    = "booking",
                title   = "Booking Accepted! 🎉",
                message = (
                    f"Your booking has been accepted for ₹{int(br.agreed_price)}. "
                    f"Advance due: ₹{advance_amt} · Event date: {br.event_date}"
                ),
                url = f"/creators/{br.creator_id}",
            )

        return Response({
            "id":              str(br.id),
            "status":          br.status,
            "agreed_price":    int(br.agreed_price),
            "advance_percent": br.advance_percent,
        })


class DeclineBookingRequest(APIView):
    def post(self, request, pk):
        try:
            br = BookingRequest.objects.get(pk=pk, status="pending")
        except BookingRequest.DoesNotExist:
            return Response({"error": "Not found or already handled"}, status=404)

        br.status = "declined"
        br.save()

        # Notify requester: booking declined
        if br.requester_id:
            Notification.objects.create(
                user_id = br.requester_id,
                type    = "booking",
                title   = "Booking Request Declined",
                message = (
                    f"Unfortunately, the creator is not available on {br.event_date}. "
                    f"Please try booking another creator."
                ),
                url = "/creators",
            )

        return Response({"id": str(br.id), "status": "declined"})


class CreatePaymentOrder(APIView):
    def post(self, request):
        br_id  = request.data.get("booking_request_id")
        amount = request.data.get("amount")

        try:
            br = BookingRequest.objects.get(pk=br_id, status="accepted")
        except BookingRequest.DoesNotExist:
            return Response({"error": "Not found or not accepted"}, status=404)

        if hasattr(br, "payment"):
            return Response({
                "razorpay_order_id": br.payment.razorpay_order_id,
                "amount":            br.payment.amount_paise,
            })

        amount_paise = int(amount) * 100

        order = rz.order.create({
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  f"br_{str(br_id)[:16]}",
            "notes":    {"booking_request_id": str(br_id)},
        })

        Payment.objects.create(
            booking_request   = br,
            razorpay_order_id = order["id"],
            amount_paise      = amount_paise,
        )

        return Response({
            "razorpay_order_id": order["id"],
            "amount":            amount_paise,
        })


class VerifyPayment(APIView):
    def post(self, request):
        order_id   = request.data.get("razorpay_order_id")
        payment_id = request.data.get("razorpay_payment_id")
        signature  = request.data.get("razorpay_signature")
        br_id      = request.data.get("booking_request_id")

        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return Response({"error": "Invalid signature"}, status=400)

        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature  = signature
        payment.status              = "captured"
        payment.save()

        br        = payment.booking_request
        br.status = "paid"
        br.save()

        # Calculate advance amount once for both notifications
        advance_amt = int(br.agreed_price * br.advance_percent / 100)

        # Notify creator: advance payment received
        creator_user_id = _creator_user_id(str(br.creator_id))
        if creator_user_id:
            Notification.objects.create(
                user_id = creator_user_id,
                type    = "payment",
                title   = "Payment Received! 💰",
                message = (
                    f"₹{advance_amt} advance has been received for "
                    f"{br.occasion_type or 'your event'} on {br.event_date}."
                ),
                url = "/creator-dashboard",
            )

        # Notify requester: payment confirmed
        if br.requester_id:
            Notification.objects.create(
                user_id = br.requester_id,
                type    = "payment",
                title   = "Payment Confirmed! ✅",
                message = (
                    f"Your advance payment of ₹{advance_amt} was successful. "
                    f"Your booking for {br.occasion_type or 'the event'} on {br.event_date} is confirmed."
                ),
                url = "/my-bookings",
            )

        return Response({"status": "paid"})