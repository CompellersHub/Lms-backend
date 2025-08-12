from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
import json
from datetime import datetime

User = get_user_model()

class NotificationManager:
    @staticmethod
    def send_user_notification(user_id, message, notification_type='generic', metadata=None):
        """
        Send real-time notification to a specific user
        """
        channel_layer = get_channel_layer()
        group_name = f"user_{user_id}"
        
        notification_data = {
            "type": "send_notification",
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            notification_data
        )
    
    @staticmethod
    def send_live_class_notification(course_id, class_data):
        """
        Send live class notification to all users in a course
        """
        channel_layer = get_channel_layer()
        group_name = f"liveclass_{course_id}"
        
        notification_data = {
            "type": "liveclass_notification",
            "class_id": str(class_data['id']),
            "title": class_data['title'],
            "start_time": class_data['start_time'].isoformat(),
            "join_url": f"/live-class/{class_data['id']}/",
            "timestamp": datetime.now().isoformat()
        }
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            notification_data
        )
        
        # Also send to each user individually
        for student_id in class_data['enrolled_students']:
            NotificationManager.send_user_notification(
                user_id=student_id,
                message=f"Live class '{class_data['title']}' is starting",
                notification_type='live_class',
                metadata={
                    'class_id': str(class_data['id']),
                    'action_url': f"/live-class/{class_data['id']}/"
                }
            )

    @staticmethod
    def broadcast_system_message(message):
        """
        Send message to all connected users
        """
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "broadcast",
            {
                "type": "system_message",
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )