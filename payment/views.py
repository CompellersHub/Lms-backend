# payment/views.py
import json
import traceback
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
from datetime import datetime, timezone

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


stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

class PaymentSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Verify Stripe is configured
        if not stripe.api_key:
            return self._error_response(
                code="STRIPE_NOT_CONFIGURED",
                message="Stripe API key not configured",
                user_message="Payment system unavailable",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # [Rest of your original implementation...]
        # Initialize logging context
        log_context = {
            "user_id": str(request.user.id),
            "endpoint": "verify-stripe-payment",
            "timestamp": datetime.utcnow().isoformat()
        }

        # 1. Validate Payment Intent ID
        payment_intent_id = request.data.get('paymentIntentId')
        if not payment_intent_id:
            logger.error("Missing paymentIntentId", extra=log_context)
            return self._error_response(
                code="MISSING_PAYMENT_INTENT",
                message="Payment verification failed: paymentIntentId is required",
                user_message="Payment information missing. Please try again.",
                status=status.HTTP_400_BAD_REQUEST,
                context=log_context
            )
        log_context["payment_intent_id"] = payment_intent_id

        # 2. Database Connection Check
        db = get_mongo_db()
        if not db:
            logger.critical("MongoDB connection failed", extra=log_context)
            return self._error_response(
                code="DATABASE_UNAVAILABLE",
                message="Database connection error",
                user_message="Our systems are busy. Please try again later.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context=log_context
            )

        try:
            # 3. Verify Stripe Payment Intent
            try:
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                logger.info("Stripe payment retrieved", extra={
                    **log_context,
                    "stripe_status": payment_intent.status
                })
            except stripe.error.StripeError as e:
                logger.error("Stripe API failed", extra={
                    **log_context,
                    "error": str(e)
                })
                return self._error_response(
                    code="STRIPE_API_ERROR",
                    message=f"Stripe verification failed: {str(e)}",
                    user_message="We couldn't verify your payment. Please try again.",
                    status=status.HTTP_400_BAD_REQUEST,
                    context=log_context
                )

            # 4. Validate Payment Status
            if payment_intent.status != 'succeeded':
                logger.error("Payment not succeeded", extra={
                    **log_context,
                    "stripe_status": payment_intent.status
                })
                return self._error_response(
                    code="PAYMENT_NOT_COMPLETED",
                    message=f"Payment status is {payment_intent.status}",
                    user_message="Your payment hasn't been completed yet.",
                    status=status.HTTP_400_BAD_REQUEST,
                    context=log_context
                )

            # 5. Extract Metadata (user_id|course_id)
            metadata = payment_intent.metadata
            custom_id = metadata.get('enrollment_ids')
            
            if not custom_id:
                logger.error("Missing enrollment_ids in metadata", extra={
                    **log_context,
                    "stripe_metadata": metadata
                })
                return self._error_response(
                    code="INVALID_PAYMENT_DATA",
                    message="Missing enrollment_ids in payment metadata",
                    user_message="Invalid payment information received.",
                    status=status.HTTP_400_BAD_REQUEST,
                    context=log_context,
                    details={"metadata": metadata}
                )

            try:
                user_id_str, course_id_str = custom_id.split('|')
                user_oid = ObjectId(user_id_str)
                course_oid = ObjectId(course_id_str)
            except (ValueError, InvalidId) as e:
                logger.error("Invalid ID format", extra={
                    **log_context,
                    "custom_id": custom_id,
                    "error": str(e)
                })
                return self._error_response(
                    code="INVALID_ID_FORMAT",
                    message=f"ID validation failed: {str(e)}",
                    user_message="We encountered an issue with your payment details.",
                    status=status.HTTP_400_BAD_REQUEST,
                    context=log_context,
                    details={"custom_id": custom_id}
                )

            # 6. Security Validation
            if user_id_str != str(request.user.id):
                logger.warning("User ID mismatch", extra={
                    **log_context,
                    "auth_user": str(request.user.id),
                    "payment_user": user_id_str
                })
                return self._error_response(
                    code="USER_MISMATCH",
                    message="Authenticated user doesn't match payment owner",
                    user_message="This payment doesn't belong to your account.",
                    status=status.HTTP_403_FORBIDDEN,
                    context=log_context,
                    details={
                        "auth_user": str(request.user.id),
                        "payment_user": user_id_str
                    }
                )

            # 7. Check Existing Enrollment
            if db.customusers.find_one({"_id": user_oid, "course._id": course_oid}):
                logger.info("Already enrolled", extra={
                    **log_context,
                    "course_id": course_id_str
                })
                return Response(
                    {
                        "status": "success",
                        "code": "ALREADY_ENROLLED",
                        "message": "User already enrolled",
                        "user_message": "You're already enrolled in this course!"
                    },
                    status=status.HTTP_200_OK
                )

            # 8. Validate Course Exists
            course = db.courses.find_one(
                {'_id': course_oid}, 
                {'name': 1, 'price': 1}
            )
            if not course:
                logger.error("Course not found", extra={
                    **log_context,
                    "course_id": course_id_str
                })
                return self._error_response(
                    code="COURSE_NOT_FOUND",
                    message="Course does not exist",
                    user_message="The course could not be found.",
                    status=status.HTTP_404_NOT_FOUND,
                    context=log_context
                )

            # 9. Process Enrollment
            try:
                # Update user's courses
                db.customusers.update_one(
                    {"_id": user_oid},
                    {"$push": {"course": {
                        "_id": course['_id'],
                        "name": course['name'],
                        "price": course['price'],
                        "enrollment_date": datetime.utcnow(),
                    }}}
                )

                # Record transaction
                db.enrollments_transactions.insert_one({
                    "user_id": user_oid,
                    "course_id": course_oid,
                    "payment_intent_id": payment_intent_id,
                    "payment_method": "stripe",
                    "timestamp": datetime.utcnow(),
                    "status": "COMPLETED",
                    "amount": payment_intent.amount / 100  # Convert from cents
                })

                logger.info("Enrollment successful", extra={
                    **log_context,
                    "course_name": course.get('name')
                })

                return Response(
                    {
                        "status": "success",
                        "message": f"Enrolled in {course.get('name', 'the course')}",
                        "user_message": f"Successfully enrolled in {course.get('name', 'the course')}!",
                        "course_id": course_id_str
                    },
                    status=status.HTTP_200_OK
                )

            except PyMongoError as e:
                logger.error("Enrollment failed", extra={
                    **log_context,
                    "error": str(e),
                    "stack_trace": traceback.format_exc()
                })
                return self._error_response(
                    code="ENROLLMENT_FAILED",
                    message="Database error during enrollment",
                    user_message="We couldn't complete your enrollment. Please contact support.",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    context=log_context
                )

        except Exception as e:
            logger.critical("Unhandled exception", extra={
                **log_context,
                "error": str(e),
                "stack_trace": traceback.format_exc()
            })
            return self._error_response(
                code="UNKNOWN_ERROR",
                message="An unexpected error occurred",
                user_message="Something went wrong. Our team has been notified.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context=log_context
            )

    def _error_response(self, code, message, user_message, status, context=None, details=None):
        """Standardized error response with logging"""
        error_data = {
            "status": "failed",
            "code": code,
            "message": message,
            "user_message": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }

        if details:
            error_data["details"] = details

        # Log to failed payments collection
        db = get_mongo_db() # Get db again for this context, or pass it if appropriate
        if context and db is not None: # <-- MODIFIED THIS LINE
            try:
                db.failed_payments.insert_one({
                    **context,
                    "error_code": code,
                    "error_message": message,
                    "details": details or {},
                    "resolved": False
                })
            except Exception as e:
                logger.error(f"Failed to log payment failure: {str(e)}")

        return Response(error_data, status=status)

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



logger = logging.getLogger(__name__)

@permission_classes([IsAuthenticated])
class VerifyPayPalOrderAndEnrollView(APIView):
    """
    Enhanced endpoint for PayPal verification and enrollment with:
    - Detailed error logging
    - Failed payment tracking
    - User-friendly messages
    - Security validation
    """

    def post(self, request):
        log_context = {} # Initialize empty to ensure it always exists

        try: # NEW: Wrap initial setup to catch errors early
            log_context = {
                "user_id": str(request.user.id),
                "endpoint": "verify-order",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.critical(f"Error initializing log_context: {e}", exc_info=True) # exc_info=True will print full traceback
            return Response(
                {
                    "status": "failed",
                    "code": "INITIALIZATION_ERROR",
                    "message": "Failed to initialize request context.",
                    "user_message": "An internal error occurred. Please try again later.",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 1. Validate Order ID
        order_id = request.data.get('order_id') # Make sure this matches your client's payload ('order_id' or 'orderID')
        if not order_id:
            logger.error("Missing orderID", extra={
                **log_context,
                "request_data": request.data
            })
            return self._error_response(
                code="MISSING_ORDER_ID",
                message="Payment verification failed: Order ID is required",
                user_message="We couldn't process your payment. Please try again.",
                status_code=status.HTTP_400_BAD_REQUEST, # Use status_code here as per your _error_response
                context=log_context
            )

        log_context["order_id"] = order_id

        # 2. Database Connection Check
        db = get_mongo_db()
        if db is None:
            logger.critical("MongoDB connection failed", extra=log_context)
            return self._error_response(
                code="DATABASE_UNAVAILABLE",
                message="Database connection error",
                user_message="Our systems are busy. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Use status_code here
                context=log_context
            )

        try: # This main try block starts here
            # 3. Verify PayPal Order by getting its details
            order_details = paypal_client._make_request(
                "GET",
                f"/v2/checkout/orders/{order_id}"
            )
            logger.critical(f"DEBUG: PayPal order_details received: {json.dumps(order_details, indent=2)}")

            # --- MODIFIED SECTION START ---

            # Safely check for 'purchase_units' and get the first one
            purchase_unit = None
            if order_details and isinstance(order_details, dict) and \
               'purchase_units' in order_details and \
               isinstance(order_details['purchase_units'], list) and \
               len(order_details['purchase_units']) > 0:
                
                purchase_unit = order_details['purchase_units'][0]
            
            # If purchase_unit couldn't be extracted, it means PayPal response was not as expected
            if not purchase_unit:
                logger.error("PayPal response missing expected 'purchase_units' or it's empty/malformed.", extra={
                    **log_context,
                    "paypal_response": order_details
                })
                return self._error_response(
                    code="INVALID_PAYPAL_RESPONSE_STRUCTURE",
                    message="PayPal order details missing 'purchase_units' or invalid structure.",
                    user_message="Invalid payment information. Please try again.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    context=log_context,
                    details={"paypal_response": order_details}
                )

            # Safely get custom_id
            custom_id = purchase_unit.get('custom_id')

            if not custom_id:
                logger.error("Missing custom_id in PayPal order purchase unit.", extra={
                    **log_context,
                    "paypal_purchase_unit": purchase_unit
                })
                return self._error_response(
                    code="MISSING_CUSTOM_ID",
                    message="Missing 'custom_id' in PayPal purchase unit.",
                    user_message="Payment details incomplete. Please contact support.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    context=log_context,
                    details={"paypal_purchase_unit": purchase_unit}
                )

            # Validate the format of custom_id and extract IDs
            try:
                user_id_str, course_id_str = custom_id.split('|')
                user_oid = ObjectId(user_id_str)
                course_oid = ObjectId(course_id_str)
            except (ValueError, InvalidId) as e:
                logger.error("Invalid ID format in custom_id from PayPal.", extra={
                    **log_context,
                    "custom_id": custom_id,
                    "error": str(e)
                })
                return self._error_response(
                    code="INVALID_CUSTOM_ID_FORMAT",
                    message=f"Invalid 'custom_id' format from PayPal: {str(e)}",
                    user_message="We encountered an issue with your payment details. Please contact support.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    context=log_context,
                    details={"custom_id": custom_id}
                )

            # 5. Security Validation
            if user_id_str != str(request.user.id):
                logger.warning("User ID mismatch", extra={
                    **log_context,
                    "auth_user": str(request.user.id),
                    "order_user": user_id_str
                })
                return self._error_response(
                    code="USER_MISMATCH",
                    message="Authenticated user doesn't match payment owner",
                    user_message="This payment doesn't belong to your account.",
                    status=status.HTTP_403_FORBIDDEN,
                    context=log_context,
                    details={
                        "auth_user": str(request.user.id),
                        "order_user": user_id_str
                    }
                )

            # 6. Check Existing Enrollment
            if db.customusers.find_one({"_id": user_oid, "course._id": course_oid}):
                logger.info("Already enrolled", extra={
                    **log_context,
                    "course_id": course_id_str
                })
                return Response(
                    {
                        "status": "success",
                        "code": "ALREADY_ENROLLED",
                        "message": "User already enrolled",
                        "user_message": "You're already enrolled in this course!"
                    },
                    status=status.HTTP_200_OK
                )

            # 7. Validate Course Exists
            course = db.courses.find_one(
                {'_id': course_oid},
                {'name': 1, 'price': 1}
            )
            if not course:
                logger.error("Course not found", extra={
                    **log_context,
                    "course_id": course_id_str
                })
                return self._error_response(
                    code="COURSE_NOT_FOUND",
                    message="Course does not exist",
                    user_message="The course could not be found.",
                    status=status.HTTP_404_NOT_FOUND,
                    context=log_context
                )

            # 8. Process Enrollment
            try:
                # Update user's courses
                db.customusers.update_one(
                    {"_id": user_oid},
                    {"$push": {"course": {
                        "_id": course['_id'],
                        "name": course['name'],
                        "price": course['price'],
                        "enrollment_date": datetime.now(timezone.utc),
                    }}}
                )

                # Record transaction
                db.enrollments_transactions.insert_one({
                    "user_id": user_oid,
                    "course_id": course_oid,
                    "order_id": order_id,
                    "payment_method": "paypal",
                    "timestamp": datetime.now(timezone.utc),
                    "status": "COMPLETED",
                    "amount": purchase_unit.get('amount', {}).get('value')
                })

                logger.info("Enrollment successful", extra={
                    **log_context,
                    "course_name": course.get('name')
                })

                return Response(
                    {
                        "status": "success",
                        "message": f"Enrolled in {course.get('name', 'the course')}",
                        "user_message": f"Successfully enrolled in {course.get('name', 'the course')}!",
                        "course_id": course_id_str
                    },
                    status=status.HTTP_200_OK
                )

            except PyMongoError as e:
                logger.error("Enrollment failed", extra={
                    **log_context,
                    "error": str(e),
                    "stack_trace": traceback.format_exc()
                })
                return self._error_response(
                    code="ENROLLMENT_FAILED",
                    message="Database error during enrollment",
                    user_message="We couldn't complete your enrollment. Please contact support.",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    context=log_context
                )

        except Exception as e:
            logger.critical("Unhandled exception during PayPal verification process", extra={
                **log_context,
                "error": str(e),
                "stack_trace": traceback.format_exc()
            })
            return self._error_response(
                code="UNKNOWN_ERROR",
                message="An unexpected error occurred",
                user_message="Something went wrong. Our team has been notified.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Use status_code here
                context=log_context
            )

    def _error_response(self, code, message, user_message, status, context=None, details=None):
        """Standardized error response with logging"""
        error_data = {
            "status": "failed",
            "code": code,
            "message": message,
            "user_message": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if details:
            error_data["details"] = details

        # Log to failed payments collection
        # Ensure db is not None before attempting to insert
        db = get_mongo_db() # Get db again for this context, or pass it if appropriate
        if context and db is not None: # <-- MODIFIED THIS LINE
            try:
                db.failed_payments.insert_one({
                    **context,
                    "error_code": code,
                    "error_message": message,
                    "details": details or {},
                    "resolved": False
                })
            except Exception as e:
                logger.error(f"Failed to log payment failure: {str(e)}")

        return Response(error_data, status=status)