import requests
import json
import logging
from django.conf import settings
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class Payl8rService:
    def __init__(self):
        self.api_key = getattr(settings, 'PAYL8R_API_KEY', '')
        self.base_url = getattr(settings, 'PAYL8R_BASE_URL', 'https://sandbox.payl8r.com/v2/')
        self.redirect_url = getattr(settings, 'PAYL8R_REDIRECT_URL', '')
        self.cancel_url = getattr(settings, 'PAYL8R_CANCEL_URL', '')
        self.is_sandbox = 'sandbox' in self.base_url
        
    def _get_headers(self):
        """Headers for public API operations"""
        return {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
        }
    
    def create_application(self, application_data):
        """
        Create a Payl8r credit application using public API key
        """
        try:
            url = urljoin(self.base_url, 'applications')
            
            # Add sandbox-specific test data if in sandbox mode
            if self.is_sandbox:
                application_data = self._add_sandbox_test_data(application_data)
            
            payload = {
                "merchant_reference": application_data['merchant_reference'],
                "amount": application_data['amount'],
                "redirect_url": self.redirect_url,
                "cancel_url": self.cancel_url,
                "customer": application_data['customer'],
                "products": application_data['products'],
                "billing_address": application_data.get('billing_address', {}),
                "shipping_address": application_data.get('shipping_address', {}),
                "metadata": application_data.get('metadata', {})
            }
            
            logger.info(f"Creating Payl8r application in {'SANDBOX' if self.is_sandbox else 'PRODUCTION'}")
            logger.debug(f"Payl8r payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url, 
                headers=self._get_headers(), 
                json=payload,
                timeout=30
            )
            
            logger.info(f"Payl8r API response status: {response.status_code}")
            logger.debug(f"Payl8r API response: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Payl8r API error: {response.status_code} - {response.text}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Payl8r API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Payl8r API error response: {e.response.text}")
            raise Exception(f"Payment provider error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Payl8r service: {str(e)}")
            raise
    
    def _add_sandbox_test_data(self, application_data):
        """
        Add test data for sandbox environment
        """
        # Ensure required fields have test data
        customer = application_data.get('customer', {})
        
        # Add test phone number for sandbox
        if not customer.get('phone'):
            customer['phone'] = '07123456789'  # UK test number
            
        # Ensure employment status is valid for testing
        if not customer.get('employment_status'):
            customer['employment_status'] = 'FULL_TIME'
            
        # Ensure monthly income is reasonable for testing
        if not customer.get('monthly_income') or customer.get('monthly_income', 0) < 1000:
            customer['monthly_income'] = 2000
            
        # Ensure residential status
        if not customer.get('residential_status'):
            customer['residential_status'] = 'HOME_OWNER'
            
        application_data['customer'] = customer
        
        # Ensure billing address has required fields
        billing_address = application_data.get('billing_address', {})
        if not billing_address.get('line_1'):
            billing_address['line_1'] = '123 Test Street'
        if not billing_address.get('town'):
            billing_address['town'] = 'Testville'
        if not billing_address.get('county'):
            billing_address['county'] = 'Testshire'
        if not billing_address.get('postcode'):
            billing_address['postcode'] = 'TE1 1ST'
            
        application_data['billing_address'] = billing_address
        
        return application_data
    
    def get_test_scenarios(self):
        """
        Get test scenarios for sandbox testing
        """
        return {
            "approved_application": {
                "description": "Application that will be approved",
                "test_data": {
                    "customer": {
                        "first_name": "Approved",
                        "last_name": "Customer",
                        "email": "approved@test.com",
                        "phone": "07123456789",
                        "date_of_birth": "1990-01-01",
                        "employment_status": "FULL_TIME",
                        "monthly_income": 2500,
                        "residential_status": "HOME_OWNER",
                        "months_at_address": 24
                    }
                }
            },
            "declined_application": {
                "description": "Application that will be declined",
                "test_data": {
                    "customer": {
                        "first_name": "Declined",
                        "last_name": "Customer", 
                        "email": "declined@test.com",
                        "phone": "07123456789",
                        "date_of_birth": "1990-01-01",
                        "employment_status": "UNEMPLOYED",
                        "monthly_income": 500,
                        "residential_status": "OTHER",
                        "months_at_address": 1
                    }
                }
            }
        }