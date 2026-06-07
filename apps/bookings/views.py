import hmac
import hashlib
import razorpay
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BookingRequest, Payment

rz = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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

        return Response({
            "id":             str(br.id),
            "status":         br.status,
            "agreed_price":   int(br.agreed_price),
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
        return Response({"id": str(br.id), "status": "declined"})


class CreatePaymentOrder(APIView):
    def post(self, request):
        br_id  = request.data.get("booking_request_id")
        amount = request.data.get("amount")  # rupees

        try:
            br = BookingRequest.objects.get(pk=br_id, status="accepted")
        except BookingRequest.DoesNotExist:
            return Response({"error": "Not found or not accepted"}, status=404)

        # Idempotency
        if hasattr(br, 'payment'):
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

        payment.booking_request.status = "paid"
        payment.booking_request.save()

        return Response({"status": "paid"})