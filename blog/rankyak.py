# blog/integrations/rankyak.py
import requests
import json
from django.conf import settings

class RankYakClient:
    def __init__(self):
        self.api_key = settings.RANKYAK_API_KEY
        self.base_url = "https://api.rankyak.com/v1"
        
    def generate_blog_content(self, title, category, tags, word_count=1500):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "title": title,
            "category": category,
            "tags": tags,
            "word_count": word_count,
            "tone": "professional",
            "style": "informative"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generate/blog",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Handle errors appropriately
            raise Exception(f"RankYak API error: {str(e)}")