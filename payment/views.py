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
                currency='usd', # Or your desired currency
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