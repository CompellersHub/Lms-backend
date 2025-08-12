# user/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Personal notifications
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    
    # Live class notifications
    re_path(r'ws/liveclass/(?P<course_id>[^/]+)/$', consumers.LiveClassConsumer.as_asgi()),
]