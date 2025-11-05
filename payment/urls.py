# payment/urls.py
from django.urls import path
from .views import *

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
    path('payl8r/create-application/', CreatePayl8rApplicationView.as_view(), name='create-payl8r-application'),
    # path('payl8r/webhook/', Payl8rWebhookView.as_view(), name='payl8r-webhook'),
    # path('payl8r/status/<str:application_id>/', Payl8rApplicationStatusView.as_view(), name='payl8r-status'),
    path('payl8r/test-scenarios/', Payl8rTestScenariosView.as_view(), name='payl8r-test-scenarios'),
    path('payl8r/simulate-webhook/', Payl8rSandboxWebhookSimulator.as_view(), name='payl8r-simulate-webhook'),
    path('payment/payl8r/debug-config/', DebugPayl8rConfigView.as_view(), name='debug-payl8r-config'),
]