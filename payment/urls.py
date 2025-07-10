# payment/urls.py
from django.urls import path
from .views import CreatePaymentIntentView, PaymentSuccessView, CreatePayPalOrderView, StripeBankTransferView, StripeTransferStatusView,  VerifyPayPalOrderAndEnrollView, BarclaysBankTransferEnrollmentView, BarclaysPaymentVerificationView, stripe_webhook

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
]