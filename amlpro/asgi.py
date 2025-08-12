# amlpro/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'amlpro.settings')
django.setup()  # This must come before importing consumers

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import user.routing  # Now safe to import

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            user.routing.websocket_urlpatterns
        )
    ),
})