# from django.urls import path
# from .views import InitiatePaymentView, CapturePaymentView, CancelPaymentView

# urlpatterns = [
#     # ... other URLs ...
#     path('courses/<int:course_id>/payment/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
#     path('courses/payment/capture/<int:course_id>/', CapturePaymentView.as_view(), name='capture-payment'),
#     path('courses/payment/cancel/<int:course_id>/', CancelPaymentView.as_view(), name='cancel-payment'),
# ]