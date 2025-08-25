# user/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication

class LiveClassConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = None  # Initialize as None
        self.user = None

    async def connect(self):
        # Get token from query parameters
        query_params = self.scope.get('query_string', b'').decode().split('&')
        token = None
        for param in query_params:
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if not token:
            await self.close(code=4001)  # Unauthorized
            return

        # Authenticate user
        try:
            self.user = await self.authenticate_user(token)
            if not self.user:
                await self.close(code=4001)
                return

            # Set up room group
            self.course_id = self.scope['url_route']['kwargs']['course_id']
            self.room_group_name = f'liveclass_{self.course_id}'

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close(code=4002)  # Internal error

    @database_sync_to_async
    def authenticate_user(self, token):
        try:
            validated_token = JWTAuthentication().get_validated_token(token)
            return JWTAuthentication().get_user(validated_token)
        except Exception:
            return None

    async def disconnect(self, close_code):
        # Safely disconnect only if room_group_name was set
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def liveclass_notification(self, event):
        """Handle live class notifications from the group"""
        await self.send(text_data=json.dumps({
            "type": "liveclass",
            "message": event["message"],
            "class_id": event["class_id"],
            "start_time": event["start_time"],
            "join_url": event["join_url"]
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    """Handles personal user notifications"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_group_name = None
        self.user_id = "test_user"  # Default for testing

    async def connect(self):
        try:
            # TEMPORARY: Accept all connections for testing
            # Remove this in production
            if self.scope["user"].is_anonymous:
                print("⚠️  Anonymous user connecting - accepting for testing")
                # For testing, we'll accept anyway but use a test user ID
                self.user_id = "test_anonymous"
            else:
                self.user_id = str(self.scope["user"].id)
            
            self.user_group_name = f"user_{self.user_id}"

            # Join user group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            
            await self.accept()
            print(f"✅ User {self.user_id} connected to notifications")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                "type": "connection",
                "message": "Connected to notifications",
                "user_id": self.user_id,
                "status": "connected"
            }))
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            await self.close(code=4002)

    async def disconnect(self, close_code):
        print(f"🔌 Disconnecting user {self.user_id} with code: {close_code}")
        
        if self.user_group_name:
            try:
                await self.channel_layer.group_discard(
                    self.user_group_name,
                    self.channel_name
                )
            except Exception as e:
                print(f"❌ Error leaving group: {e}")

    async def send_notification(self, event):
        """Handle notifications from channel layer"""
        try:
            await self.send(text_data=json.dumps({
                "type": "notification",
                "message": event["message"],
                "timestamp": event.get("timestamp"),
                "data": event.get("data", {})
            }))
        except Exception as e:
            print(f"❌ Error sending notification: {e}")