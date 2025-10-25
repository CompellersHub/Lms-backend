import requests
import logging
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class Payl8rService:
    def __init__(self):
        self.merchant_id = settings.PAYL8R_CONFIG['MERCHANT_ID']
        self.merchant_key = settings.PAYL8R_CONFIG['MERCHANT_KEY']
        self.base_url = settings.PAYL8R_CONFIG['BASE_URL']
    
    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'X-MERCHANT-ID': self.merchant_id,
            'X-MERCHANT-KEY': self.merchant_key,
        }
    
    def create_application(self, application_data):
        """
        Create a new Payl8r credit application
        """
        url = f"{self.base_url}/applications"
        
        payload = {
            "merchant_reference": application_data['merchant_reference'],
            "total_amount": application_data['total_amount'],
            "products": application_data['products'],
            "customer": application_data['customer'],
            "redirect_urls": application_data.get('redirect_urls', {}),
            "metadata": application_data.get('metadata', {})
        }
        
        try:
            logger.info(f"Creating Payl8r application: {application_data['merchant_reference']}")
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Payl8r application created: {result.get('id')}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Payl8r API Error: {str(e)}", extra={
                "merchant_reference": application_data['merchant_reference'],
                "error": str(e)
            })
            return None
    
    def get_application_status(self, application_id):
        """
        Check Payl8r application status
        """
        url = f"{self.base_url}/applications/{application_id}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Payl8r API Status Error: {str(e)}", extra={
                "application_id": application_id,
                "error": str(e)
            })
            return None
    
    def get_affordability(self, amount):
        """
        Get affordability calculator data
        """
        url = f"{self.base_url}/affordability-calculator"
        
        payload = {
            "amount": amount
        }
        
        try:
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Payl8r Affordability Error: {str(e)}")
            return None