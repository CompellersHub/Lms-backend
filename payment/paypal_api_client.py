# payment/paypal_api_client.py
import uuid
import requests
import json
import logging
import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class PayPalAPIClient:
    def __init__(self):
        # Base URL for PayPal API (sandbox or live)
        self.base_url = "https://api-m.paypal.com" if settings.PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"
        self._access_token = None
        self._token_expires_at = 0 # Unix timestamp

    def _get_access_token(self):
        """Fetches a new PayPal access token if expired or not set."""
        # Check if token is still valid (with a 60-second buffer)
        if self._access_token and self._token_expires_at > datetime.datetime.now().timestamp() + 60:
            return self._access_token

        logger.info("Fetching new PayPal access token...")
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        # Use HTTP Basic Auth for token endpoint
        auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET)
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                auth=auth,
                data=data,
                timeout=10 # Set a timeout for the request
            )
            response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
            token_data = response.json()
            
            self._access_token = token_data["access_token"]
            # Calculate expiration time, subtracting a buffer to refresh early
            self._token_expires_at = datetime.datetime.now().timestamp() + token_data.get("expires_in", 32400) - 300 # 5-minute buffer

            logger.info("Successfully fetched new PayPal access token.")
            return self._access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching PayPal access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"PayPal token response error: {e.response.text}")
            raise Exception(f"Failed to get PayPal access token: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during PayPal token fetch: {e}")
            raise

    def _make_request(self, method, endpoint, json_data=None):
        """Helper to make authenticated requests to PayPal API v2."""
        access_token = self._get_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": str(uuid.uuid4()) # Important for idempotency
        }
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=15)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=15)
            else:
                raise ValueError("Unsupported HTTP method")

            response.raise_for_status() # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal API request failed ({method} {endpoint}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"PayPal API error details: {json.dumps(error_details, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"PayPal API raw error response: {e.response.text}")
            raise Exception(f"PayPal API call failed: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during PayPal API request: {e}")
            raise

    def create_order(self, order_payload):
        """Calls PayPal Orders API v2 to create an order."""
        return self._make_request("POST", "/v2/checkout/orders", json_data=order_payload)

    def capture_order(self, order_id):
        """Calls PayPal Orders API v2 to capture an order."""
        return self._make_request("POST", f"/v2/checkout/orders/{order_id}/capture")

# Instantiate the client globally for reuse
paypal_client = PayPalAPIClient()