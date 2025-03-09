import paypalrestsdk
from django.conf import settings

def configure_paypal():
    paypalrestsdk.configure({
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    })

def create_payment(amount, currency, description, return_url, cancel_url):
    configure_paypal()

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": return_url,
            "cancel_url": cancel_url
        },
        "transactions": [{
            "amount": {
                "total": str(amount),
                "currency": currency
            },
            "description": description
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return payment, link.href
    else:
        return None, payment.error

def execute_payment(payment_id, payer_id):
    configure_paypal()

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        return True, payment
    else:
        return False, payment.error