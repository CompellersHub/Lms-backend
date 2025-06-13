# payment/urls.py
from django.urls import path
from .views import CreatePaymentIntentView, PaymentSuccessView, CreatePayPalOrderView, CapturePayPalOrderView

app_name = 'payment'

urlpatterns = [
    path('create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    # This one doesn't take URL arguments, it expects data in the POST body
    path('payment-success/', PaymentSuccessView.as_view(), name='payment-success-webhook-alternative'),
    path('paypal/create-order/', CreatePayPalOrderView.as_view(), name='paypal-create-order'),
    path('paypal/capture-order/', CapturePayPalOrderView.as_view(), name='paypal-capture-order'),
]