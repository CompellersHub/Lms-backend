from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .client import create_payment, execute_payment

class CreatePayPalPayment(APIView):
    def post(self, request):
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        description = request.data.get('description', 'Payment')
        return_url = request.data.get('return_url')
        cancel_url = request.data.get('cancel_url')

        if not all([amount, return_url, cancel_url]):
            return Response({'error': 'Missing required parameters'}, status=status.HTTP_400_BAD_REQUEST)

        payment, approval_url = create_payment(amount, currency, description, return_url, cancel_url)

        if approval_url:
            return Response({'approval_url': approval_url}, status=status.HTTP_200_OK)
        else:
            return Response({'error': payment}, status=status.HTTP_400_BAD_REQUEST)

class ExecutePayPalPayment(APIView):
    def get(self, request):
        payment_id = request.GET.get('paymentId')
        payer_id = request.GET.get('PayerID')

        if not all([payment_id, payer_id]):
            return Response({'error': 'Missing paymentId or PayerID'}, status=status.HTTP_400_BAD_REQUEST)

        success, payment_details = execute_payment(payment_id, payer_id)

        if success:
            return Response({'message': 'Payment successful', 'payment_details': payment_details.to_dict()}, status=status.HTTP_200_OK)
        else:
            return Response({'error': payment_details}, status=status.HTTP_400_BAD_REQUEST)

class PaypalWebhook(APIView):
    def post(self, request):
        #verify webhook signature here.
        #process the webhook data.
        print(request.data)
        return Response(status=status.HTTP_200_OK)