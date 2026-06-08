from django.urls import path
from . import views

urlpatterns = [
    path("booking-requests/create/",            views.CreateBookingRequest.as_view()),  # ← add this
    path("booking-requests/<uuid:pk>/accept/",  views.AcceptBookingRequest.as_view()),
    path("booking-requests/<uuid:pk>/decline/", views.DeclineBookingRequest.as_view()),
    path("payments/create-order/",              views.CreatePaymentOrder.as_view()),
    path("payments/verify/",                    views.VerifyPayment.as_view()),
]