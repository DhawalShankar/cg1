import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import BookingRequest, Payment


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
        return Response({"id": str(br.id), "status": "declined"})


class CreatePaymentOrder(APIView):
    def post(self, request):
        return Response({"error": "Payment not configured yet"}, status=503)


class VerifyPayment(APIView):
    def post(self, request):
        return Response({"error": "Payment not configured yet"}, status=503)