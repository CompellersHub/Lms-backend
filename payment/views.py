# payments/views.py
import datetime
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import stripe
from django.conf import settings
from bson.objectid import ObjectId
import logging

# Import your MongoDB utility and CourseSerializer
from courses.serializer import CourseSerializer
# Assuming your CustomUserSerializer is in 'user.serializers'
from user.serializer import CustomUserSerializer # Import CustomUserSerializer
from courses.mongo_utils import get_mongo_db

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# ... (CreatePaymentIntentView remains the same as in the previous "no webhook" response)

class PaymentSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        db = get_mongo_db()
        user_id = str(request.user.id) # This is the string representation of the user's MongoDB ObjectId
        payment_intent_id = request.data.get('payment_intent_id')
        course_id = request.data.get('course_id') # The ObjectId string of the course

        if not payment_intent_id or not course_id:
            return Response(
                {"error": "Payment Intent ID and Course ID are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Retrieve the PaymentIntent directly from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # 2. Verify PaymentIntent status
            if payment_intent.status == 'succeeded':
                # Verify metadata against request data for security
                # Ensure the course_id and user_id in Stripe's metadata match what's expected
                if payment_intent.metadata.get('course_id') != course_id or \
                   payment_intent.metadata.get('user_id') != user_id:
                    logger.warning(f"Metadata mismatch for PaymentIntent {payment_intent_id}. "
                                   f"Expected course_id {course_id}, user_id {user_id}. "
                                   f"Actual metadata: {payment_intent.metadata}")
                    return Response(
                        {"error": "Payment validation failed: Metadata mismatch."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 3. Fetch the full course document from your `courses` collection
                # This is important because you store the full course object in the user's 'course' array
                course_document = db.courses.find_one({"_id": ObjectId(course_id)})
                if not course_document:
                    logger.error(f"Course {course_id} not found in DB during fulfillment for PaymentIntent {payment_intent_id}.")
                    return Response(
                        {"error": "Course not found for enrollment."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Optional: Re-verify price if critical
                price_from_db = course_document.get('price')
                amount_paid = payment_intent.amount / 100 # Convert cents to dollars
                if abs(price_from_db - amount_paid) > 0.01:
                    logger.warning(f"Price mismatch for course {course_id} and payment {payment_intent_id}. "
                                   f"DB price: {price_from_db}, Paid: {amount_paid}.")
                    # Decide how to handle: log, alert admin, refund, etc.
                    # For now, we proceed.

                # 4. Check for idempotency: Prevent double-enrollment
                # We need to check if this specific PaymentIntent ID has already led to an enrollment
                # AND if the user is already enrolled in THIS course.
                # Since you embed the course, we check if the _id already exists in the user's 'course' array.

                # First, retrieve the user document
                user_document = db.customusers.find_one({"_id": ObjectId(user_id)})
                if not user_document:
                    logger.error(f"User {user_id} not found during fulfillment for PaymentIntent {payment_intent_id}.")
                    return Response(
                        {"error": "User not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Check if the course is already present in the user's 'course' array
                # Note: `course_document` has an `_id` field. `ObjectId(course_id)` is a BSON ObjectId.
                is_already_enrolled = any(
                    item.get('_id') == ObjectId(course_id)
                    for item in user_document.get('course', [])
                )
                
                if is_already_enrolled:
                    logger.info(f"User {user_id} already enrolled in course {course_id}. Idempotent fulfillment for PaymentIntent {payment_intent_id}.")
                    return Response({"message": "Course already enrolled."}, status=status.HTTP_200_OK)

                # 5. Enroll the user in the course by pushing the full course document
                # Make sure the `_id` field of the embedded course document is correct
                course_document_to_embed = {
                    k: (ObjectId(v) if k == '_id' else v) # Ensure _id is an ObjectId if it wasn't already
                    for k, v in course_document.items()
                }

                update_result = db.customusers.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$push": {"course": course_document_to_embed}} # Push the entire course document
                )

                if update_result.modified_count > 0:
                    logger.info(f"User {user_id} successfully enrolled in course {course_id} via direct success callback.")
                    # Optionally, record a separate enrollment transaction for audit purposes
                    db.enrollments_transactions.insert_one({
                        "user_id": ObjectId(user_id),
                        "course_id": ObjectId(course_id),
                        "payment_intent_id": payment_intent_id,
                        "amount_paid": amount_paid,
                        "currency": payment_intent.currency,
                        "enrollment_date": datetime.datetime.utcnow(),
                        "status": "completed"
                    })
                    return Response({"message": "Payment successful and course enrolled!"}, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Failed to enroll user {user_id} in course {course_id}. User not found or no modification occurred.")
                    return Response(
                        {"error": "Failed to enroll user in course."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            elif payment_intent.status == 'requires_action':
                logger.warning(f"PaymentIntent {payment_intent_id} requires action. Frontend should handle redirect.")
                return Response(
                    {"message": "Payment requires further action (e.g., 3D Secure)."},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            else:
                logger.warning(f"PaymentIntent {payment_intent_id} has status: {payment_intent.status}")
                return Response(
                    {"error": f"Payment not successful. Status: {payment_intent.status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error during fulfillment for PaymentIntent {payment_intent_id}: {e}")
            return Response(
                {"error": f"Stripe API error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ObjectId.InvalidId:
            logger.error(f"Invalid ObjectId format for user_id ({user_id}) or course_id ({course_id}).")
            return Response(
                {"error": "Invalid ID format in request."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("An unexpected error occurred during payment fulfillment.")
            return Response(
                {"error": "An internal server error occurred during fulfillment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )