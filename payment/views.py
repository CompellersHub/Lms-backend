# payment/views.py
import json
import traceback
from django.http import HttpResponse
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
from datetime import datetime, timedelta, timezone
import os
from django.views.decorators.csrf import csrf_exempt
stripe.api_key = os.getenv('STRIPE_TEST_kEY')



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
                enrollment_date = datetime.now(timezone.utc)
                db.customusers.update_one(
                    {"_id": user_oid},
                    {"$push": {"course": {
                        "_id": course['_id'],
                        "name": course['name'],
                        "price": course['price'],
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