from django.urls import path
from .views import CreatePayPalPayment, ExecutePayPalPayment, PaypalWebhook

urlpatterns = [
    path('create/', CreatePayPalPayment.as_view(), name='create_paypal_payment'),
    path('execute/', ExecutePayPalPayment.as_view(), name='execute_paypal_payment'),
    path('webhook/', PaypalWebhook.as_view(), name='paypal_webhook'),
]