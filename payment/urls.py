# payment/urls.py
from django.urls import path
from .views import CheckPayl8rStatusView, CreatePayl8rApplicationView, CreatePaymentIntentView, Payl8rAffordabilityView, Payl8rWebhookView, PaymentSuccessView, CreatePayPalOrderView, StripeBankTransferView, StripeTransferStatusView,  VerifyPayPalOrderAndEnrollView, BarclaysBankTransferEnrollmentView, BarclaysPaymentVerificationView, stripe_webhook

app_name = 'payment'

urlpatterns = [
    path('create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    # This one doesn't take URL arguments, it expects data in the POST body
    path('payment-success/', PaymentSuccessView.as_view(), name='payment-success-webhook-alternative'),
    path('paypal/create-order/', CreatePayPalOrderView.as_view(), name='paypal-create-order'),
    path('paypal/verify-order/',  VerifyPayPalOrderAndEnrollView.as_view(), name='paypal-capture-order'),
    path('payment/barclays-transfer/', BarclaysBankTransferEnrollmentView.as_view()),
    path('admin/verify-barclays-payment/', BarclaysPaymentVerificationView.as_view()),
    path('payment/stripe-bank-transfer/', StripeBankTransferView.as_view()),
    path('payment/stripe-transfer-status/<str:payment_intent_id>/', StripeTransferStatusView.as_view()),
    path('stripe-webhook/', stripe_webhook),
    path('payment/payl8r/affordability/', Payl8rAffordabilityView.as_view(), name='payl8r-affordability'),
    path('payment/payl8r/application/', CreatePayl8rApplicationView.as_view(), name='create-payl8r-application'),
    path('payment/payl8r/status/<str:application_id>/', CheckPayl8rStatusView.as_view(), name='check-payl8r-status'),
    path('webhooks/payl8r/', Payl8rWebhookView.as_view(), name='payl8r-webhook'),
]