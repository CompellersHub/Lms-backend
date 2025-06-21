import stripe
from django.conf import settings
import os

stripe.api_key = os.getenv('STRIPE_TEST_kEY')