from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(APIView):
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response([], status=200)
        notifs = Notification.objects.filter(user_id=user_id).order_by("-created_at")[:50]
        return Response(NotificationSerializer(notifs, many=True).data)

class MarkReadView(APIView):
    def post(self, request, pk):
        Notification.objects.filter(pk=pk).update(is_read=True)
        return Response({"status": "ok"})

class MarkAllReadView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if user_id:
            Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
        return Response({"status": "ok"})