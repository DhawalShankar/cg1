from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.CharField()  # UUID → string
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "message", "url", "is_read", "created_at"]