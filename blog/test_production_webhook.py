import requests
import json
import os

def test_webhook():
    # Your production webhook URL
    webhook_url = "https://api.titanscareers.com/blogs/webhooks/ranyak/blog-created"
    
    # Get secret from environment variable or input
    webhook_secret = os.environ.get('RANKYAK_WEBHOOK_SECRET')
    if not webhook_secret:
        webhook_secret = input("Enter your RankYak webhook secret: ")
    
    # Test payload
    payload = {
        "title": "Test Blog from Production Script",
        "slug": "test-production-script",
        "category": "Testing",
        "tags": ["test", "production", "script"],
        "excerpt": "Testing the production webhook endpoint with a script",
        "content": "# Production Script Test\n\nThis is testing the production webhook endpoint with a Python script.",
        "status": "draft",
        "featured_image": "https://titanscareers.s3.amazonaws.com/blogs/test-image.jpg"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-RankYak-Secret": webhook_secret
    }
    
    print("Testing production webhook...")
    print(f"URL: {webhook_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"Response: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Production webhook test successful!")
        else:
            print("❌ Production webhook test failed!")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_webhook()
