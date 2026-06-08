from django.urls import path
from .views import NotificationListView, MarkReadView, MarkAllReadView

urlpatterns = [
    path("",              NotificationListView.as_view()),   # GET  ?user_id=xxx
    path("<uuid:pk>/read/", MarkReadView.as_view()),         # POST
    path("read-all/",     MarkAllReadView.as_view()),        # POST {user_id}
]