# management/commands/test_webhook.py
from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings
import json

class Command(BaseCommand):
    help = 'Test the RankYak webhook integration'

    def handle(self, *args, **options):
        client = Client()
        
        test_payload = {
            "title": "Test Blog Post from Management Command",
            "slug": "test-management-command",
            "category": "Testing",
            "tags": ["test", "management", "command"],
            "excerpt": "Test from Django management command.",
            "content": "# Test from Management Command\n\nThis is a test from a Django management command.",
            "status": "draft",
            "featured_image": "https://titanscareers.s3.amazonaws.com/blogs/test-image.jpg",  # Add this
            "test": True
        }
        
        headers = {
            "HTTP_X_RANKYAK_SECRET": settings.RANKYAK_WEBHOOK_SECRET,
            "content_type": "application/json"
        }
        
        self.stdout.write("Testing RankYak webhook...")
        
        response = client.post(
            '/blog/webhooks/rankyak/blog-created/',
            data=json.dumps(test_payload),
            **headers
        )
        
        if response.status_code == 201:
            self.stdout.write(
                self.style.SUCCESS('✅ Webhook test successful!')
            )
            self.stdout.write(f"Response: {response.json()}")
        else:
            self.stdout.write(
                self.style.ERROR('❌ Webhook test failed!')
            )
            self.stdout.write(f"Status: {response.status_code}")
            self.stdout.write(f"Response: {response.content}")