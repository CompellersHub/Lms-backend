# payment/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings # To access Stripe keys and MongoDB URI
from bson import ObjectId
import stripe
import logging
import datetime
from .paypal_api_client import paypal_client 
import uuid
from rest_framework.decorators import authentication_classes, permission_classes
from pymongo.errors import PyMongoError 
from bson.errors import InvalidId 


# Make sure this import matches where your get_mongo_db function is located
from courses.mongo_utils import get_mongo_db # Assuming it's in courses app

logger = logging.getLogger(__name__)

class CreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available for CreatePaymentIntentView.")
            return Response(
                {"error": "Database connection error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {"error": "Course ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course_oid = ObjectId(course_id)
        except Exception:
            return Response(
                {"error": "Invalid Course ID format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = db.courses.find_one({"_id": course_oid})

        if not course:
            return Response(
                {"error": "Course not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Convert price to cents (Stripe expects integer in smallest currency unit)
            amount_in_cents = int(course['price'] * 100) 

            # User object from request.user (set by JWTAuthentication)
            # request.user should have an 'id' attribute (from AbstractBaseUser)
            # and a '_mongo_doc' attribute (from your MongoAuthBackend if implemented as discussed)
            user_id = str(request.user.id) 
            user_email = request.user.email # Assuming your user model has an email field

            # Create a PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency='GBP', # Or your desired currency
                metadata={
                    'course_id': course_id,
                    'user_id': user_id,
                    'course_price_at_payment': str(course['price']), # Store original price
                    'user_email': user_email, # Useful for Stripe dashboard
                },
                # Optional: description, receipt_email etc.
                description=f"Enrollment in {course['name']} for {user_email}",
            )

            return Response({
                "clientSecret": payment_intent.client_secret,
                "publishableKey": settings.STRIPE_PUBLISHABLE_KEY,
                "course_id": course_id,
                "payment_intent_id": payment_intent.id, # Useful for tracking
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating Payment Intent: {e}")
            return Response(
                {"error": f"Stripe error: {e.user_message or e.code}"},
                status=status.HTTP_400_BAD_REQUEST # Or 500 depending on the specific error
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return Response(
                {"error": "An unexpected error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentSuccessView(APIView):
    # This view could be called by your frontend after a successful payment client-side.
    # For production, it's highly recommended to use a Stripe Webhook for server-side fulfillment.
    # However, based on your tests, you're using this direct callback approach.
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available for PaymentSuccessView.")
            return Response(
                {"error": "Database connection error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_intent_id = request.data.get('payment_intent_id')
        course_id = request.data.get('course_id')

        if not payment_intent_id or not course_id:
            return Response(
                {"error": "Payment Intent ID and Course ID are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving PaymentIntent {payment_intent_id}: {e}")
            return Response(
                {"error": f"Stripe API error: {e.user_message or e.code}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Check payment status
        if payment_intent.status != 'succeeded':
            logger.warning(f"PaymentIntent {payment_intent_id} has status: {payment_intent.status}")
            return Response(
                {"error": f"Payment not successful. Status: {payment_intent.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve metadata from the PaymentIntent (safer than relying solely on client data)
        # However, the client is sending `course_id` too, so we'll use that as primary input
        # and compare with metadata for consistency.
        # It's better practice to solely rely on metadata from the PaymentIntent for fulfillment.
        retrieved_course_id_from_stripe = payment_intent.metadata.get('course_id')
        retrieved_user_id_from_stripe = payment_intent.metadata.get('user_id')
        course_price_at_payment = float(payment_intent.metadata.get('course_price_at_payment', 0))

        # Basic validation against client-provided data (optional but good)
        if str(request.user.id) != retrieved_user_id_from_stripe or course_id != retrieved_course_id_from_stripe:
            logger.error(f"Mismatched data for PaymentIntent {payment_intent_id}: User ID or Course ID mismatch.")
            # This could be a security concern or a data integrity issue
            return Response(
                {"error": "Data mismatch or unauthorized fulfillment attempt."},
                status=status.HTTP_403_FORBIDDEN # Or 400
            )

        try:
            user_oid = ObjectId(request.user.id) # Use the authenticated user's ID
            course_oid = ObjectId(course_id)
        except Exception:
            return Response(
                {"error": "Invalid ID format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_doc = db.customusers.find_one({"_id": user_oid})
        if not user_doc:
            logger.error(f"User {user_oid} not found during payment success fulfillment.")
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        course_doc = db.courses.find_one({"_id": course_oid})
        if not course_doc:
            logger.error(f"Course {course_oid} not found during payment success fulfillment.")
            return Response(
                {"error": "Course not found for enrollment."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user is already enrolled
        if any(c['_id'] == course_oid for c in user_doc.get('course', [])):
            logger.info(f"User {user_oid} already enrolled in course {course_oid}. Idempotent fulfillment for PaymentIntent {payment_intent_id}.")
            return Response(
                {"message": "Course already enrolled."},
                status=status.HTTP_200_OK # Still a success, but no action needed
            )
        
        # If not enrolled, enroll the user and record transaction
        try:
            # Add course to user's 'course' array
            db.customusers.update_one(
                {"_id": user_oid},
                {"$push": {"course": {
                    "_id": course_doc['_id'],
                    "name": course_doc['name'],
                    "price": course_doc['price'],
                    "enrollment_date": datetime.datetime.utcnow(),
                    # Add any other course details you want to embed for the user
                }}}
            )

            # Record the transaction
            db.enrollments_transactions.insert_one({
                "user_id": user_oid,
                "course_id": course_oid,
                "payment_intent_id": payment_intent_id,
                "amount_paid": course_price_at_payment, # Use the price from metadata
                "currency": payment_intent.currency,
                "status": "succeeded",
                "timestamp": datetime.datetime.utcnow(),
            })

            logger.info(f"User {user_oid} successfully enrolled in course {course_oid} via direct success callback.")
            return Response(
                {"message": "Payment successful and course enrolled!"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error enrolling user {user_oid} in course {course_oid}: {e}")
            return Response(
                {"error": "Error processing enrollment. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 

@permission_classes([IsAuthenticated])
class CreatePayPalOrderView(APIView):
    """
    Endpoint to create a PayPal Order (v2 API).
    The frontend calls this to get an orderID.
    """
    def post(self, request):
        user = request.user
        course_id = request.data.get('course_id') # Expecting course_id in body

        if not course_id:
            return Response({"error": "course_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available for CreatePayPalOrderView.")
            return Response(
                {"error": "Database connection error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # 1. Fetch user details
            mongo_user = db.customusers.find_one({"_id": ObjectId(user.id)})
            if not mongo_user:
                logger.error(f"MongoDB user not found for ID: {user.id}")
                return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

            # 2. Fetch course details
            course_oid = ObjectId(course_id)
            course_from_mongo = db.courses.find_one({'_id': course_oid}, {'name': 1, 'price': 1})
            if not course_from_mongo:
                logger.error(f"Course not found in MongoDB: {course_id}")
                return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
            
            course_name = course_from_mongo.get('name')
            course_price = course_from_mongo.get('price')

            if course_price is None:
                logger.error(f"Course price not found in MongoDB: {course_id}")
                return Response({'error': 'Course price not found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Ensure price is a string with 2 decimal places for PayPal
            total_price_str = f"{float(course_price):.2f}"
            currency = "GBP" # IMPORTANT: Ensure this matches your PayPal account and course price

            # 3. Construct PayPal Order Payload
            order_payload = {
                "intent": "CAPTURE", # We intend to capture funds directly
                "purchase_units": [{
                    "amount": {
                        "currency_code": currency,
                        "value": total_price_str,
                        "breakdown": { # Optional, but good for detailed amounts
                            "item_total": {
                                "currency_code": currency,
                                "value": total_price_str
                            }
                        }
                    },
                    "description": f"Payment for course: {course_name}",
                    "items": [{
                        "name": course_name,
                        "unit_amount": {
                            "currency_code": currency,
                            "value": total_price_str
                        },
                        "quantity": "1"
                    }],
                    # Pass custom data that you'll need back in the capture view
                    "custom_id": f"{user.id}|{course_id}", # User ID and Course ID
                    "soft_descriptor": "COURSE_ENROLL", # Appears on buyer's statement
                }],
                "application_context": {
                    "return_url": request.build_absolute_uri('/payment/paypal-return-url/'), # Dummy URL, frontend handles final redirect
                    "cancel_url": request.build_absolute_uri('/payment/paypal-cancel-url/'), # Dummy URL, frontend handles final redirect
                    "brand_name": "YOUR_BRAND_NAME", # Your brand name shown on PayPal
                    "landing_page": "BILLING", # Can be 'LOGIN' or 'BILLING'
                    "shipping_preference": "NO_SHIPPING", # No shipping needed for digital goods
                    "user_action": "PAY_NOW" # Show "Pay Now" button on PayPal
                }
            }

            # 4. Call PayPal API to create the order
            paypal_response = paypal_client.create_order(order_payload)
            order_id = paypal_response.get("id")

            if order_id:
                logger.info(f"PayPal Order created: {order_id} for user {user.id} and course {course_id}")
                return Response({'orderID': order_id}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to get orderID from PayPal: {paypal_response}")
                return Response({'error': 'Failed to create PayPal order.'}, status=status.HTTP_400_BAD_REQUEST)

        except InvalidId:
            logger.error(f"Invalid course_id format: {course_id}")
            return Response({'error': 'Invalid course_id format'}, status=status.HTTP_400_BAD_REQUEST)
        except PyMongoError as e:
            logger.error(f"MongoDB operation error in CreatePayPalOrderView: {e}")
            return Response({'error': 'Database error during order creation. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error creating PayPal order: {str(e)}", exc_info=True)
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@permission_classes([IsAuthenticated])
class CapturePayPalOrderView(APIView):
    """
    Endpoint to capture a PayPal Order (v2 API).
    The frontend calls this from the onApprove callback.
    """
    def post(self, request):
        order_id = request.data.get('orderID') # Expecting orderID from frontend
        
        if not order_id:
            return Response({"error": "orderID is required."}, status=status.HTTP_400_BAD_REQUEST)

        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection not available for CapturePayPalOrderView.")
            return Response(
                {"error": "Database connection error. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # 1. Call PayPal API to capture the order
            paypal_response = paypal_client.capture_order(order_id)
            
            # Check the status of the capture
            if paypal_response.get("status") == "COMPLETED":
                # Extract user_id and course_id from custom_id passed during order creation
                # The custom_id is embedded in the purchase_units -> payments -> captures -> custom_id
                # Or you can fetch the order details via GET /v2/checkout/orders/{order_id}
                
                # For simplicity, let's assume we store the custom_id or fetch order details if needed.
                # In a robust system, you'd fetch the order details and verify
                # custom_id = paypal_response['purchase_units'][0]['payments']['captures'][0]['custom_id']
                # user_id_str, course_id_str = custom_id.split('|')

                # As a fallback, since user is authenticated, we can use request.user.id
                user_oid = ObjectId(request.user.id) 

                # To get the course_id related to this specific order, 
                # it's best to fetch the order details from PayPal or store it temporarily.
                # For this example, let's assume we already have course_id passed to frontend (which is likely true)
                # or better, fetch the order details from PayPal API to retrieve the 'custom_id' field.
                # Let's get it from PayPal's order details API
                order_details = paypal_client._make_request("GET", f"/v2/checkout/orders/{order_id}")
                custom_id_from_paypal = order_details['purchase_units'][0].get('custom_id')
                
                if not custom_id_from_paypal:
                    logger.error(f"Custom ID not found in PayPal order {order_id}. Cannot enroll user.")
                    return Response({"error": "Order details incomplete. Cannot enroll."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                user_id_from_paypal_str, course_id_str = custom_id_from_paypal.split('|')
                
                # IMPORTANT: Verify that user_id_from_paypal_str matches request.user.id for security
                if user_id_from_paypal_str != str(request.user.id):
                    logger.error(f"Security Warning: User ID mismatch during PayPal capture. Authenticated user {request.user.id} vs PayPal order user {user_id_from_paypal_str}")
                    # You might want to log this and potentially revert transaction or flag for manual review
                    return Response({"error": "Security check failed. User mismatch."}, status=status.HTTP_403_FORBIDDEN)


                course_oid = ObjectId(course_id_str) # Use the course_id from custom_id
                
                # 2. Check if user is already enrolled (Idempotency)
                user_doc = db.customusers.find_one({"_id": user_oid})
                if not user_doc:
                    logger.error(f"User {user_oid} not found in MongoDB during PayPal capture (post-order).")
                    # This is an unusual state if authentication passed. Log and handle.
                    return Response({"error": "User profile not found for enrollment."}, status=status.HTTP_404_NOT_FOUND)

                if any(c['_id'] == course_oid for c in user_doc.get('course', [])):
                    logger.info(f"User {user_oid} already enrolled in course {course_oid}. Idempotent fulfillment for PayPal order {order_id}.")
                    return Response(
                        {'message': 'Payment successful, but course was already enrolled.'},
                        status=status.HTTP_200_OK
                    )
                
                # 3. Enroll the user
                course_doc = db.courses.find_one({'_id': course_oid}, {'name': 1, 'price': 1})
                if not course_doc:
                    logger.error(f"Course {course_oid} not found in MongoDB during PayPal capture (post-order).")
                    return Response({'error': 'Course not found for enrollment.'}, status=status.HTTP_404_NOT_FOUND)

                db.customusers.update_one(
                    {"_id": user_oid},
                    {"$push": {"course": {
                        "_id": course_doc['_id'],
                        "name": course_doc['name'],
                        "price": course_doc['price'],
                        "enrollment_date": datetime.datetime.utcnow(),
                    }}}
                )

                # 4. Record the transaction
                capture_details = paypal_response['purchase_units'][0]['payments']['captures'][0]
                db.enrollments_transactions.insert_one({
                    "user_id": user_oid,
                    "course_id": course_oid,
                    "order_id": order_id, # PayPal Order ID
                    "capture_id": capture_details['id'], # PayPal Capture ID
                    "payer_id": paypal_response['payer']['payer_id'], # Payer ID from completed order
                    "amount_paid": float(capture_details['amount']['value']),
                    "currency": capture_details['amount']['currency_code'],
                    "status": capture_details['status'],
                    "payment_method": "paypal",
                    "timestamp": datetime.datetime.utcnow(),
                })

                logger.info(f"PayPal Order {order_id} successfully captured and user {user_oid} enrolled in course {course_oid}.")
                return Response(
                    {'message': f'Payment successful! You are now enrolled in {course_doc.get("name", "this course")}'},
                    status=status.HTTP_200_OK
                )

            else:
                status_detail = paypal_response.get("status", "UNKNOWN")
                logger.error(f"Failed to capture PayPal Order {order_id}. Status: {status_detail}. Response: {paypal_response}")
                # You might want to provide more specific error messages based on PayPal status
                return Response({'error': f'Failed to capture PayPal order. Status: {status_detail}'}, status=status.HTTP_400_BAD_REQUEST)

        except InvalidId:
            logger.error("Invalid ObjectId format encountered during PayPal capture.")
            return Response({'error': 'Invalid ID format.'}, status=status.HTTP_400_BAD_REQUEST)
        except PyMongoError as e:
            logger.error(f"MongoDB operation error in CapturePayPalOrderView: {e}")
            return Response({'error': 'Database error during payment capture. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error capturing PayPal order: {str(e)}", exc_info=True)
            return Response({'error': f'An unexpected error occurred during payment capture: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)