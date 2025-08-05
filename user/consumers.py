# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = str(self.scope["user"].id)  # Ensure string
        self.group_name = f"notifications_{self.user_id}"  # Consistent format
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()