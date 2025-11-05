# payment/views.py
import hashlib
import hmac
import json
import traceback
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.conf import settings # To access Stripe keys and MongoDB URI
from bson import ObjectId
import stripe
import logging
import datetime
import time
from django.urls import reverse
import logging
import traceback
import uuid

from .services.payl8r_service import Payl8rService


from payment.serializers.payl8r_serializers import CreatePayl8rApplicationSerializer, Payl8rApplicationSerializer
from .services import generate_virtual_account
from .paypal_api_client import paypal_client 
import uuid
from rest_framework.decorators import authentication_classes, permission_classes
from pymongo.errors import PyMongoError 
from bson.errors import InvalidId 
from datetime import datetime, timedelta, timezone
import os
from django.views.decorators.csrf import csrf_exempt
from payment.services.validation import validate_course
from payment.services.enrollment import enroll_student
from payment.services.generate_virtual_account import generate_virtual_account

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')



# Make sure this import matches where your get_mongo_db function is located
from courses.mongo_utils import get_mongo_db # Assuming it's in courses app

logger = logging.getLogger(__name__)

class CreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        log_context = {
            "user_id": str(request.user.id),
            "endpoint": "create-payment-intent",
            "timestamp": datetime.utcnow().isoformat()
        }

        # 1. Verify Stripe API Key
        if not stripe.api_key:
            logger.critical("Stripe API key not configured", extra=log_context)
            return Response(
                {"status": "failed", "code": "STRIPE_NOT_CONFIGURED",
                 "message": "Payment system configuration error",
                 "user_message": "Our payment system is currently unavailable."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 2. Database Connection Check
        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection failed", extra=log_context)
            return Response(
                {"status": "failed", "code": "DATABASE_UNAVAILABLE",
                 "message": "Database connection error",
                 "user_message": "Our systems are busy. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3. Validate Course ID
        course_id = request.data.get('course_id')
        if not course_id:
            logger.error("Missing course_id", extra={**log_context, "request_data": request.data})
            return Response(
                {"status": "failed", "code": "MISSING_COURSE_ID",
                 "message": "Course ID is required",
                 "user_message": "Please select a course to enroll in."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course_oid = ObjectId(course_id)
            log_context["course_id"] = course_id
        except Exception as e:
            logger.error("Invalid Course ID format", extra={
                **log_context, "error": str(e), "provided_course_id": course_id})
            return Response(
                {"status": "failed", "code": "INVALID_COURSE_ID",
                 "message": "Invalid Course ID format",
                 "user_message": "The course information is invalid. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Fetch Complete Course Details
        try:
            course = db.courses.find_one(
                {"_id": course_oid},
                {
                    "name": 1, "price": 1, "course_image": 1, 
                    "instructor": 1, "description": 1, "preview_id": 1,
                    "preview_description": 1, "category": 1, "level": 1,
                    "estimated_time": 1, "curriculum": 1
                }
            )
            if not course:
                logger.error("Course not found", extra=log_context)
                return Response(
                    {"status": "failed", "code": "COURSE_NOT_FOUND",
                     "message": "Course not found",
                     "user_message": "The course could not be found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            log_context.update({
                "course_name": course.get('name'),
                "course_price": course.get('price'),
                "instructor": course.get('instructor', {}).get('first_name', 'Unknown')
            })
        except PyMongoError as e:
            logger.error("Database error fetching course", extra={
                **log_context, "error": str(e), "stack_trace": traceback.format_exc()})
            return Response(
                {"status": "failed", "code": "DATABASE_ERROR",
                 "message": "Error fetching course details",
                 "user_message": "We couldn't retrieve course information. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. Create Payment Intent with enriched metadata
        try:
            amount_in_cents = int(course['price'] * 100)
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency='GBP',
                metadata={
                    'course_id': course_id,
                    'user_id': str(request.user.id),
                    'course_name': course.get('name'),
                    'course_image': course.get('course_image', ''),
                    'course_instructor': f"{course.get('instructor', {}).get('first_name', '')} {course.get('instructor', {}).get('last_name', '')}",
                    'user_email': request.user.email,
                    'enrollment_ids': f"{request.user.id}|{course_id}",
                    'course_description': course.get('description', '')[:100] + '...' if course.get('description') else '',
                    'course_level': course.get('level', '')
                },
                description=f"Enrollment in {course['name']} for {request.user.email}",
            )

            logger.info("PaymentIntent created", extra={
                **log_context, "payment_intent_id": payment_intent.id})

            # Prepare course data for response
            response_course_data = {
                "id": str(course['_id']),
                "name": course.get('name'),
                "course_image": course.get('course_image'),
                "instructor": course.get('instructor'),
                "price": course.get('price'),
                "description": course.get('description'),
                "preview": {
                    "id": course.get('preview_id'),
                    "description": course.get('preview_description')
                },
                "category": course.get('category'),
                "level": course.get('level'),
                "estimated_time": course.get('estimated_time')
            }

            return Response({
                "status": "success",
                "clientSecret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "course": response_course_data,
                "amount": course['price'],
                "currency": "GBP"
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            logger.error("Stripe API error", extra={
                **log_context, "error_type": type(e).__name__,
                "error_code": getattr(e, 'code', None),
                "error_message": str(e)})
            return Response(
                {"status": "failed", "code": "STRIPE_ERROR",
                 "message": f"Payment processing error: {e.user_message or e.code}",
                 "user_message": "We couldn't process your payment. Please try again.",
                 "stripe_code": e.code},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.critical("Unexpected error", extra={
                **log_context, "error": str(e), "stack_trace": traceback.format_exc()})
            return Response(
                {"status": "failed", "code": "UNKNOWN_ERROR",
                 "message": "An unexpected error occurred",
                 "user_message": "Something went wrong. Our team has been notified."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error("Invalid payload in webhook")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature in webhook")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=400)

    # Handle payment success
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        return handle_successful_payment(payment_intent)
    
    return HttpResponse(status=200)


def handle_successful_payment(payment_intent):
    db = get_mongo_db()
    if db is None:
        logger.error("Database connection failed during webhook processing")
        return HttpResponse(status=500)

    metadata = payment_intent.metadata
    custom_id = metadata.get('enrollment_ids')
    
    if not custom_id:
        logger.error("Missing enrollment_ids in metadata from webhook")
        return HttpResponse(status=400)

    try:
        user_id_str, course_id_str = custom_id.split('|')
        user_oid = ObjectId(user_id_str)
        course_oid = ObjectId(course_id_str)
    except (ValueError, InvalidId) as e:
        logger.error(f"Invalid ID format in webhook: {str(e)}")
        return HttpResponse(status=400)

    # Check existing enrollment
    if db.customusers.find_one({"_id": user_oid, "course._id": course_oid}):
        logger.info("Already enrolled (webhook)")
        return HttpResponse(status=200)

    # Get complete course details
    course = db.courses.find_one(
        {'_id': course_oid}, 
        {
            "name": 1, "price": 1, "course_image": 1, 
            "instructor": 1, "description": 1, "category": 1,
            "level": 1, "estimated_time": 1, "curriculum": 1
        }
    )
    if not course:
        logger.error("Course not found in webhook")
        return HttpResponse(status=404)

    # Process enrollment with full course data
    try:
        enrollment_date = datetime.utcnow()
        
        # Prepare curriculum data (simplified for storage)
        simplified_curriculum = [
            {
                "title": module.get('title'),
                "video_count": len(module.get('video', [])),
                "notes": bool(module.get('course_note'))
            }
            for module in course.get('curriculum', [])
        ]
        
        # Update user's courses with full details
        db.customusers.update_one(
            {"_id": user_oid},
            {"$push": {"course": {
                "_id": course['_id'],
                "name": course.get('name'),
                "price": course.get('price'),
                "course_image": course.get('course_image'),
                "instructor": course.get('instructor'),
                "description": course.get('description'),
                "category": course.get('category'),
                "level": course.get('level'),
                "estimated_time": course.get('estimated_time'),
                "curriculum": simplified_curriculum,
                "enrollment_date": enrollment_date,
                "progress": {
                    "completed_modules": 0,
                    "total_modules": len(simplified_curriculum),
                    "last_accessed": None
                }
            }}}
        )

        # Record transaction with full details
        db.enrollments_transactions.insert_one({
            "user_id": user_oid,
            "course_id": course_oid,
            "course_name": course.get('name'),
            "payment_intent_id": payment_intent.id,
            "payment_method": "stripe",
            "timestamp": enrollment_date,
            "status": "COMPLETED",
            "amount": payment_intent.amount / 100,
            "processed_via_webhook": True,
            "course_data": {
                "image": course.get('course_image'),
                "instructor": course.get('instructor'),
                "category": course.get('category'),
                "level": course.get('level')
            }
        })

        logger.info("Webhook enrollment successful")
        return HttpResponse(status=200)

    except PyMongoError as e:
        logger.error(f"Database error during webhook enrollment: {str(e)}")
        return HttpResponse(status=500)


class PaymentSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        log_context = {
            "user_id": str(request.user.id),
            "endpoint": "payment-success",
            "timestamp": datetime.utcnow().isoformat()
        }

        payment_intent_id = request.data.get('payment_intent_id')
        if not payment_intent_id:
            return self._error_response(
                code="MISSING_PAYMENT_INTENT",
                message="Payment intent ID required",
                user_message="Payment information missing",
                status=status.HTTP_400_BAD_REQUEST,
                context=log_context
            )

        log_context["payment_intent_id"] = payment_intent_id

        try:
            # 1. Verify payment with Stripe first
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status != 'succeeded':
                return self._error_response(
                    code="PAYMENT_NOT_COMPLETED",
                    message="Payment not completed",
                    user_message="Payment not yet completed",
                    status=status.HTTP_400_BAD_REQUEST,
                    context=log_context
                )

            db = get_mongo_db()
            if db is None:
                return self._error_response(
                    code="DATABASE_ERROR",
                    message="Database connection failed",
                    user_message="System error. Please try again.",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    context=log_context
                )

            # 2. Check if user is enrolled in any course (new approach)
            user_id = ObjectId(request.user.id)
            user = db.customusers.find_one(
                {"_id": user_id},
                {"course": 1}  # Only return courses field
            )
            
            if not user:
                return self._error_response(
                    code="USER_NOT_FOUND",
                    message="User not found",
                    user_message="System error. Please contact support.",
                    status=status.HTTP_404_NOT_FOUND,
                    context=log_context
                )

            # Get the most recently enrolled course
            enrolled_courses = user.get('course', [])
            if not enrolled_courses:
                return Response({
                    "status": "processing",
                    "message": "Payment received, processing enrollment",
                    "user_message": "Your payment was successful! We're setting up your course access.",
                    "check_again": True
                }, status=status.HTTP_202_ACCEPTED)

            # Assuming the last course is the most recent enrollment
            enrolled_course = enrolled_courses[-1]
            
            # 3. Now check/record the transaction
            transaction = db.enrollments_transactions.find_one({
                "payment_intent_id": payment_intent_id,
                "user_id": user_id,
                "course_id": enrolled_course['_id']
            })

            # If no transaction exists, create one
            if not transaction:
                try:
                    transaction = {
                        "payment_intent_id": payment_intent_id,
                        "user_id": user_id,
                        "course_id": enrolled_course['_id'],
                        "amount": payment_intent.amount_received / 100,  # Convert from cents
                        "currency": payment_intent.currency.upper(),
                        "timestamp": datetime.utcnow(),
                        "status": "completed"
                    }
                    db.enrollments_transactions.insert_one(transaction)
                except Exception as e:
                    logger.error("Failed to record transaction", extra={
                        **log_context, 
                        "error": str(e)
                    })
                    # Continue anyway since enrollment is already complete

            # Prepare success response
            return Response({
                "status": "success",
                "message": "Enrollment confirmed",
                "user_message": f"Successfully enrolled in {enrolled_course.get('name', 'the course')}!",
                "course": {
                    "id": str(enrolled_course['_id']),
                    "name": enrolled_course.get('name'),
                    "course_image": enrolled_course.get('course_image'),
                    # ... other course fields
                },
                "payment": {
                    "order_id": payment_intent_id,
                    "amount": payment_intent.amount_received / 100,
                    "currency": payment_intent.currency.upper(),
                    "date": datetime.utcnow().isoformat()
                },
                "access": {
                    "granted": True,
                    "type": "full",
                    "start_date": enrolled_course.get('enrollment_date', datetime.utcnow()).isoformat(),
                    "expires": None
                }
            })

        except stripe.error.StripeError as e:
            return self._error_response(
                code="STRIPE_ERROR",
                message=str(e),
                user_message="Payment verification failed",
                status=status.HTTP_400_BAD_REQUEST,
                context=log_context
            )
        except Exception as e:
            logger.error("Error in PaymentSuccessView", extra={
                **log_context, 
                "error": str(e), 
                "stack_trace": traceback.format_exc()
            })
            return self._error_response(
                code="UNKNOWN_ERROR",
                message="An unexpected error occurred",
                user_message="Something went wrong. Please try again.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                context=log_context
            )

    # _error_response remains the same

    def _error_response(self, code, message, user_message, status, context=None, details=None):
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
        db = get_mongo_db()
        if context and db is not None:  # Changed from 'if context and db'
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
                status=status.HTTP_400_BAD_REQUEST, # Use status_code here as per your _error_response
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR, # Use status_code here
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
                    status=status.HTTP_400_BAD_REQUEST,
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
                    status=status.HTTP_400_BAD_REQUEST,
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
                    status=status.HTTP_400_BAD_REQUEST,
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
                {'name': 1, 'price': 1, 'course_image': 1}
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
                enrollment_date = datetime.now(timezone.utc)
                db.customusers.update_one(
                    {"_id": user_oid},
                    {"$push": {"course": {
                        "_id": course['_id'],
                        "name": course['name'],
                        "price": course['price'],
                        "image": course['course_image'],
                        "enrollment_date": enrollment_date,
                    }}}
                )

                # Record transaction
                db.enrollments_transactions.insert_one({
                    "user_id": user_oid,
                    "course_id": course_oid,
                    "order_id": order_id,
                    "payment_method": "paypal",
                    "timestamp": enrollment_date,
                    "status": "COMPLETED",
                    "amount": purchase_unit.get('amount', {}).get('value')
                })

                logger.info("Enrollment successful", extra={
                    **log_context,
                    "course_name": course.get('name')
                })

                # Prepare response with additional fields
                return Response(
                    {
                        "status": "success",
                        "message": f"Enrolled in {course.get('name', 'the course')}",
                        "user_message": f"Successfully enrolled in {course.get('name', 'the course')}!",
                        "course_id": course_id_str,
                        "order_id": order_id,  # Added order_id
                        "course_access": {     # Added course_access details
                            "access_granted": True,
                            "access_type": "premium",  # or "basic" depending on your course access you want to grant
                            "expiration_date": (enrollment_date + timedelta(days=365)).isoformat(),  # 1 year access
                            "features_available": ["video_lessons", "course_libraries", "continous_assessments", "certificate"],
                            "enrollment_date": enrollment_date.isoformat()
                        }
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
        """Standardized error response with logging
        
        Args:
            code: Machine-readable error code
            message: Technical error message
            user_message: Friendly message for users
            status: HTTP status code (use status.HTTP_400_BAD_REQUEST etc.)
            context: Additional logging context
            details: Debug details
        """
        error_data = {
            "status": "failed",
            "code": code,
            "message": message,
            "user_message": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if details:
            error_data["details"] = details

        # Log to MongoDB if available
        db = get_mongo_db()
        if context and db is not None:  # Changed from 'if context and db'
            try:
                db.failed_payments.insert_one({
                    **context,
                    "error_code": code,
                    "error_message": message,
                    "details": details or {},
                    "resolved": False,
                    "timestamp": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.error(f"Failed to log payment failure: {str(e)}")

        return Response(error_data, status=status)
    
# views.py
class BarclaysBankTransferEnrollmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Provides Barclays bank details for manual transfer
        Returns:
        - Bank account details
        - Unique payment reference
        - Payment instructions
        """
        try:
            # Validate course
            course_id = request.data['course_id']
            if not ObjectId.is_valid(course_id):
                return Response(
                    {"status": "error", "message": "Invalid course ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            course = validate_course(course_id)
            if not course:
                return Response(
                    {"status": "error", "message": "Invalid course ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate unique reference (GB date format)
            ref_date = datetime.now().strftime('%d%m%y')
            reference = f"{settings.BARCLAYS_BANK_CONFIG['PAYMENT_REF_PREFIX']}-{ref_date}-{request.user.id[:6]}"

            # Record the transaction
            transfer_data = {
                "user_id": ObjectId(request.user.id),
                "course_id": ObjectId(course_id),
                "amount": float(course['price']),
                "currency": course.get('currency', 'GBP'),
                "status": "AWAITING_PAYMENT",
                "reference": reference,
                "bank_details": {
                    "bank_name": "Barclays",
                    "sort_code": "20-11-43"
                },
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=7),
                "metadata": {
                    "course_name": course['name'],
                    "user_email": request.user.email,
                }
            }
            
            db.bank_transfers.insert_one(transfer_data)

            # Prepare payment instructions
            return Response({
                "status": "awaiting_payment",
                "payment_instructions": {
                    "for_uk_payments": {
                        "account_name": settings.BARCLAYS_BANK_CONFIG['ACCOUNT_NAME'],
                        "account_number": settings.BARCLAYS_BANK_CONFIG['ACCOUNT_NUMBER'],
                        "sort_code": settings.BARCLAYS_BANK_CONFIG['SORT_CODE'],
                        "reference": reference,
                        "amount": f"£{course['price']:.2f}",
                        "payment_note": f"Course: {course['name']}"
                    },
                    "for_international_payments": {
                        "beneficiary_name": settings.BARCLAYS_BANK_CONFIG['ACCOUNT_NAME'],
                        "iban": settings.BARCLAYS_BANK_CONFIG['IBAN'],
                        "swift_bic": settings.BARCLAYS_BANK_CONFIG['SWIFT_BIC'],
                        "bank_address": settings.BARCLAYS_BANK_CONFIG['BANK_ADDRESS'],
                        "reference": reference,
                        "amount": f"{course['price']:.2f} {course.get('currency', 'GBP')}",
                        "payment_note": f"Education Payment - {course['name']}"
                    },
                    "important_notes": [
                        "Include the reference in your payment",
                        "Payments may take 1-3 business days to clear",
                        "Send payment proof to finance@yourdomain.com",
                        "Contact support for any payment issues"
                    ]
                },
                "verification_options": {
                    "upload_receipt_url": reverse('upload-payment-proof'),
                    "email_receipt_to": settings.BARCLAYS_BANK_CONFIG['SUPPORT_EMAIL'],
                    "contact_support": settings.BARCLAYS_BANK_CONFIG['SUPPORT_PHONE']
                },
                "reference": reference,
                "expires_at": (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Barclays transfer setup failed: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "message": "Payment setup failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
db = get_mongo_db()

# views.py


# webhooks.py
class BarclaysPaymentVerificationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Special verification for Barclays payments with:
        - Sort code validation
        - Reference format checking
        - GBP amount validation
        """
        try:
            reference = request.data['reference']
            action = request.data['action']
            admin_notes = request.data.get('notes', '')

            transfer = db.bank_transfers.find_one({"reference": reference})
            if not transfer:
                return Response(
                    {"status": "error", "message": "Transaction not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Barclays-specific validation
            if transfer['bank_details']['sort_code'] != '20-11-43':
                return Response(
                    {"status": "error", "message": "Invalid sort code for Barclays"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if action == 'approve':
                # Verify GBP amount
                if transfer['currency'] != 'GBP':
                    return Response(
                        {"status": "warning", "message": "Non-GBP payment requires manual review"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Process enrollment
                enrollment_data = {
                    "user_id": transfer['user_id'],
                    "course_id": transfer['course_id'],
                    "payment_method": "barclays_transfer",
                    "amount": transfer['amount'],
                    "currency": "GBP",
                    "reference": reference,
                    "verified_by": request.user.email
                }

                enroll_student(enrollment_data)

                db.bank_transfers.update_one(
                    {"_id": transfer['_id']},
                    {
                        "$set": {
                            "status": "COMPLETED",
                            "verified_at": datetime.utcnow(),
                            "admin_notes": admin_notes,
                            "bank_verified": True
                        }
                    }
                )

                return Response({
                    "status": "success",
                    "message": "Barclays payment verified and enrollment processed"
                })

            elif action == 'reject':
                db.bank_transfers.update_one(
                    {"_id": transfer['_id']},
                    {
                        "$set": {
                            "status": "REJECTED",
                            "rejected_at": datetime.utcnow(),
                            "rejection_reason": admin_notes
                        }
                    }
                )
                return Response({
                    "status": "success",
                    "message": "Payment rejected"
                })

        except Exception as e:
            logger.error(f"Barclays verification failed: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "message": "Verification failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



# views.py
from stripe.error import StripeError

class StripeBankTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Creates a Stripe-hosted bank transfer payment
        """
        try:
            # 1. Validate course
            course_id = request.data['course_id']
            course = validate_course(course_id)
            if not course:
                return Response(
                    {"error": "Invalid course"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. Create Stripe PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(course['price'] * 100),  # In pennies
                currency='gbp',
                payment_method_types=['customer_balance'],
                payment_method_data={
                    'type': 'customer_balance',
                },
                payment_method_options={
                    'customer_balance': {
                        'funding_type': 'bank_transfer',
                        'bank_transfer': {
                            'type': 'gb_bank_transfer',  # For UK banks
                            'requested_address_types': ['sort_code'],
                        }
                    }
                },
                metadata={
                    'course_id': str(course['_id']),
                    'user_id': str(request.user.id),
                    'payment_type': 'bank_transfer'
                }
            )

            # 3. Get bank transfer details
            bank_transfer_details = payment_intent.next_action['display_bank_transfer_instructions']
            
            # 4. Save to database
            db.stripe_bank_transfers.insert_one({
                'user_id': ObjectId(request.user.id),
                'course_id': ObjectId(course_id),
                'payment_intent_id': payment_intent.id,
                'amount': course['price'],
                'currency': 'GBP',
                'status': 'requires_payment_method',
                'bank_details': {
                    'sort_code': bank_transfer_details['sort_code'],
                    'account_number': bank_transfer_details['account_number'],
                    'bank_name': bank_transfer_details['bank_name'],
                    'reference': bank_transfer_details['reference']
                },
                'created_at': datetime.utcnow()
            })

            return Response({
                'status': 'requires_bank_transfer',
                'bank_instructions': {
                    'amount': f"£{course['price']:.2f}",
                    'sort_code': bank_transfer_details['sort_code'],
                    'account_number': bank_transfer_details['account_number'],
                    'bank_name': bank_transfer_details['bank_name'],
                    'reference': bank_transfer_details['reference'],
                    'due_by': payment_intent.next_action['display_bank_transfer_instructions']['expires_at']
                },
                'payment_intent_id': payment_intent.id
            })

        except StripeError as e:
            return Response(
                {'error': str(e.user_message)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
# webhooks.py
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_CONFIG['WEBHOOK_SECRET']
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Handle bank transfer completion
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        if payment_intent.metadata.get('payment_type') == 'bank_transfer':
            handle_stripe_bank_transfer(payment_intent)

    return HttpResponse(status=200)

def handle_stripe_bank_transfer(payment_intent):
    """Process completed Stripe bank transfer"""
    # 1. Update Stripe transfer record
    transfer = db.stripe_bank_transfers.find_one_and_update(
        {'payment_intent_id': payment_intent.id},
        {'$set': {
            'status': 'succeeded',
            'completed_at': datetime.utcnow()
        }},
        return_document=True
    )

    if not transfer:
        logger.error(f"Stripe transfer not found: {payment_intent.id}")
        return

    # 2. Enroll student
    enroll_student({
        'user_id': transfer['user_id'],
        'course_id': transfer['course_id'],
        'payment_method': 'stripe_bank_transfer',
        'amount': transfer['amount'],
        'transaction_id': payment_intent.id
    })


class StripeTransferStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_intent_id):
        try:
            # 1. Get from Stripe
            pi = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # 2. Get from our DB
            transfer = db.stripe_bank_transfers.find_one({
                'payment_intent_id': payment_intent_id,
                'user_id': ObjectId(request.user.id)
            })

            if not transfer:
                return Response(
                    {'error': 'Transfer not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 3. Prepare response
            response = {
                'status': pi.status,
                'amount': transfer['amount'],
                'currency': transfer['currency'],
                'bank_details': transfer.get('bank_details', {}),
                'last_updated': transfer.get('updated_at', transfer['created_at']).isoformat()
            }

            if pi.status == 'succeeded':
                response['course_access'] = True
            elif pi.status == 'processing':
                response['estimated_completion'] = (datetime.utcnow() + timedelta(hours=24)).isoformat()

            return Response(response)

        except StripeError as e:
            return Response(
                {'error': str(e.user_message)},
                status=status.HTTP_400_BAD_REQUEST
            )







@permission_classes([IsAuthenticated])
class CreatePayl8rApplicationView(APIView):
    """
    Create a Payl8r credit application with sandbox support
    """
    def post(self, request):
        log_context = {
            "user_id": str(request.user.id),
            "endpoint": "create-payl8r-application",
            "timestamp": datetime.utcnow().isoformat()
        }

        # 1. Validate Payl8r configuration
        if not getattr(settings, 'PAYL8R_API_KEY', ''):
            logger.error("Payl8r API key not configured", extra=log_context)
            return Response(
                {"status": "failed", "code": "PAYL8R_NOT_CONFIGURED",
                 "message": "Payl8r payment system not configured",
                 "user_message": "Payment option currently unavailable."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        db = get_mongo_db()
        if db is None:
            logger.error("MongoDB connection failed", extra=log_context)
            return Response(
                {"status": "failed", "code": "DATABASE_UNAVAILABLE",
                 "message": "Database connection error",
                 "user_message": "Our systems are busy. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        course_id = request.data.get('course_id')
        if not course_id:
            logger.error("Missing course_id", extra={**log_context, "request_data": request.data})
            return Response(
                {"status": "failed", "code": "MISSING_COURSE_ID",
                 "message": "Course ID is required",
                 "user_message": "Please select a course to enroll in."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course_oid = ObjectId(course_id)
            course = db.courses.find_one({"_id": course_oid})
            
            if not course:
                logger.error("Course not found", extra=log_context)
                return Response(
                    {"status": "failed", "code": "COURSE_NOT_FOUND",
                     "message": "Course not found",
                     "user_message": "The course could not be found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            log_context.update({
                "course_name": course.get('name'),
                "course_price": course.get('price')
            })

            # Generate merchant reference
            merchant_reference = f"COURSE_{course_id}_{request.user.id}_{int(time.time())}"
            
            # Prepare application data
            customer_data = request.data.get('customer', {})
            application_data = {
                "merchant_reference": merchant_reference,
                "amount": float(course['price']),
                "redirect_url": request.build_absolute_uri(reverse('payl8r-redirect')),
                "cancel_url": request.build_absolute_uri(reverse('payl8r-cancel')),
                "customer": {
                    "title": customer_data.get('title', ''),
                    "first_name": customer_data.get('first_name', request.user.first_name),
                    "last_name": customer_data.get('last_name', request.user.last_name),
                    "email": request.user.email,
                    "phone": customer_data.get('phone', ''),
                    "date_of_birth": customer_data.get('date_of_birth'),
                    "employment_status": customer_data.get('employment_status'),
                    "monthly_income": int(customer_data.get('monthly_income', 0)),
                    "residential_status": customer_data.get('residential_status'),
                    "months_at_address": int(customer_data.get('months_at_address', 0))
                },
                "products": [{
                    "name": course['name'],
                    "quantity": 1,
                    "unit_price": float(course['price']),
                    "image_url": course.get('course_image', '') or ''
                }],
                "billing_address": request.data.get('billing_address', {}),
                "metadata": {
                    "user_id": str(request.user.id),
                    "course_id": course_id,
                    "course_name": course['name'],
                    "user_email": request.user.email,
                    "environment": "sandbox"  # Mark as sandbox transaction
                }
            }

            # Add shipping address if provided
            if request.data.get('shipping_address'):
                application_data["shipping_address"] = request.data.get('shipping_address')

            # Create Payl8r application
            payl8r_service = Payl8rService()
            payl8r_response = payl8r_service.create_application(application_data)

            # Store application in database
            db.payl8r_applications.insert_one({
                "application_id": payl8r_response.get('application_id'),
                "merchant_reference": merchant_reference,
                "user_id": ObjectId(request.user.id),
                "course_id": course_oid,
                "amount": course['price'],
                "status": "PENDING",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "metadata": application_data['metadata'],
                "application_data": application_data,
                "environment": "sandbox"  # Mark as sandbox
            })

            logger.info("Payl8r sandbox application created successfully", extra={
                **log_context, 
                "application_id": payl8r_response.get('application_id'),
                "merchant_reference": merchant_reference
            })

            return Response({
                "status": "success",
                "application_id": payl8r_response.get('application_id'),
                "redirect_url": payl8r_response.get('redirect_url'),
                "merchant_reference": merchant_reference,
                "environment": "sandbox",
                "message": "Credit application created successfully"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Payl8r application creation failed", extra={
                **log_context, 
                "error": str(e),
                "stack_trace": traceback.format_exc()
            })
            return Response(
                {"status": "failed", "code": "PAYL8R_APPLICATION_FAILED",
                 "message": f"Credit application failed: {str(e)}",
                 "user_message": "We couldn't process your credit application. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )


@permission_classes([IsAuthenticated])
class Payl8rTestScenariosView(APIView):
    """
    Get test scenarios for sandbox testing
    """
    def get(self, request):
        payl8r_service = Payl8rService()
        scenarios = payl8r_service.get_test_scenarios()
        
        return Response({
            "status": "success",
            "environment": "sandbox",
            "test_scenarios": scenarios,
            "notes": [
                "Use these test scenarios in sandbox mode",
                "Modify customer data to test different outcomes",
                "All transactions are simulated in sandbox"
            ]
        })



class Payl8rSandboxWebhookSimulator(APIView):
    """
    Simulate Payl8r webhooks for sandbox testing
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Simulate webhook calls for testing
        """
        try:
            application_id = request.data.get('application_id')
            simulated_status = request.data.get('status', 'ACCEPTED')
            
            if not application_id:
                return Response({
                    "error": "application_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create simulated webhook payload
            webhook_payload = {
                "application_id": application_id,
                "status": simulated_status,
                "merchant_reference": f"TEST_{int(time.time())}",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Process the simulated webhook
            db = get_mongo_db()
            if db:
                # Update application status
                db.payl8r_applications.update_one(
                    {"application_id": application_id},
                    {
                        "$set": {
                            "status": simulated_status,
                            "updated_at": datetime.utcnow(),
                            "webhook_data": webhook_payload,
                            "simulated_webhook": True
                        }
                    }
                )

                # If status is ACCEPTED, enroll the user
                if simulated_status == "ACCEPTED":
                    application = db.payl8r_applications.find_one({"application_id": application_id})
                    if application:
                        user_id = application['user_id']
                        course_id = application['course_id']
                        
                        # Check if already enrolled
                        if not db.customusers.find_one({"_id": user_id, "course._id": course_id}):
                            course = db.courses.find_one({"_id": course_id})
                            if course:
                                enrollment_date = datetime.utcnow()
                                db.customusers.update_one(
                                    {"_id": user_id},
                                    {"$push": {"course": {
                                        "_id": course_id,
                                        "name": course.get('name'),
                                        "price": course.get('price'),
                                        "course_image": course.get('course_image'),
                                        "instructor": course.get('instructor'),
                                        "description": course.get('description'),
                                        "enrollment_date": enrollment_date,
                                        "payment_method": "payl8r_sandbox"
                                    }}}
                                )

            return Response({
                "status": "success",
                "message": f"Simulated webhook with status: {simulated_status}",
                "webhook_payload": webhook_payload
            })

        except Exception as e:
            logger.error("Sandbox webhook simulation failed", extra={
                "error": str(e),
                "stack_trace": traceback.format_exc()
            })
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# Add to your views.py temporarily
@permission_classes([IsAuthenticated])
class DebugPayl8rConfigView(APIView):
    def get(self, request):
        from django.conf import settings
        
        config_status = {
            'PAYL8R_API_KEY': bool(getattr(settings, 'PAYL8R_API_KEY', None)),
            'PAYL8R_API_KEY_VALUE': getattr(settings, 'PAYL8R_API_KEY', 'NOT_SET')[:10] + '...' if getattr(settings, 'PAYL8R_API_KEY', None) else 'NOT_SET',
            'PAYL8R_BASE_URL': getattr(settings, 'PAYL8R_BASE_URL', 'NOT_SET'),
            'PAYL8R_REDIRECT_URL': getattr(settings, 'PAYL8R_REDIRECT_URL', 'NOT_SET'),
            'environment_variables': {
                'PAYL8R_API_KEY in os.environ': 'PAYL8R_API_KEY' in os.environ,
            }
        }
        
        return Response(config_status)