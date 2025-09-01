import os
import re
import pytz
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from bson.objectid import ObjectId, InvalidId
from datetime import datetime
from bson.errors import InvalidId
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from rest_framework.permissions import AllowAny
import paypalrestsdk
from courses.models import Course, CourseEnrollment
import io
from PyPDF2 import PdfReader, PdfWriter
from fpdf import FPDF
from pymongo import MongoClient
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from django.contrib.auth import get_user_model
from django.utils import timezone
from brevo_python.rest import ApiException
from brevo_python import ContactsApi, CreateContact
from brevo_python import AddContactToList
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sib_api_v3_sdk import ContactsApi, CreateContact


from user.serializer import CustomUserSerializer
from user.tasks import send_course_registration_email
from .serializer import (
    CategorySerializer,
    ConsultationSerializer,
    CourseSerializer,
    CourseLibrarySerializer,
    AssignmentSerializer,
    EventRegistrationSerializer,
    EventSerializer,
    SubmissionSerializer,
    VideoSerializer,
    ModuleInCourseSerializer,
    # NotificationSerializer,
    LiveClassSerializer,
    CompletionCertificateSerializer
)
from .models import LiveClass
from .mongo_utils import get_mongo_db
import logging
from pymongo.errors import PyMongoError



db = get_mongo_db()

# PAYPAD_API_KEY = "your_paypad_api_key"  # Replace with your actual Paypad API Key
# PAYPAD_BASE_URL = "https://paypad.com/api/v1"  # Adjust if Paypad has a different base URL

# @login_required
# def create_course_order(request):
#     if request.method == "POST":
#         db = get_mongo_db()
#         user_id = str(request.user.id)  # Assuming you store Django user ID as string in MongoDB

#         course_ids = request.POST.getlist('course_ids[]')

#         if not course_ids:
#             return JsonResponse({"error": "No courses selected"}, status=400)

#         total_price = 0
#         order_data = {
#             "user_id": user_id,
#             "total_price": 0,
#             "payment_status": "pending",
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#             "order_items": []
#         }
#         order_result = db.course_orders.insert_one(order_data)
#         order_id = str(order_result.inserted_id)

#         for course_id in course_ids:
#             course = db.courses.find_one({"_id": ObjectId(course_id)})
#             if course:
#                 total_price += course.get('price', 0)
#                 item_data = {
#                     "order_id": order_id,
#                     "course_id": course_id,
#                     "price": course.get('price', 0)
#                 }
#                 db.course_order_items.insert_one(item_data)

#         db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"total_price": total_price}})

#         return JsonResponse({"message": "Order created successfully", "order_id": order_id})
#     return JsonResponse({"error": "Invalid request"}, status=400)

# def initiate_paypad_payment(request, order_id):
#     db = get_mongo_db()
#     order = db.course_orders.find_one({"_id": ObjectId(order_id), "user_id": str(request.user.id)})

#     if not order:
#         return JsonResponse({"error": "Order not found"}, status=404)

#     payload = {
#         "amount": order.get("total_price", 0),
#         "currency": "NGN",  # Change if using a different currency
#         "reference": f"order-{order_id}",
#         "callback_url": f"{settings.SITE_URL}/paypad/callback/",
#         "customer": {
#             "email": request.user.email,
#             "name": request.user.get_full_name(),
#         }
#     }

#     headers = {
#         "Authorization": f"Bearer {PAYPAD_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     response = requests.post(f"{PAYPAD_BASE_URL}/payments", json=payload, headers=headers)

#     if response.status_code == 200:
#         data = response.json()
#         db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"paypad_reference": data.get("reference")}})
#         return redirect(data.get("payment_url"))  # Redirect user to Paypad payment page

#     return JsonResponse({"error": "Payment initiation failed"}, status=400)

# @csrf_exempt
# def paypad_callback(request):
#     if request.method == "POST":
#         db = get_mongo_db()
#         data = request.POST  # Assuming Paypad sends POST data
#         reference = data.get("reference")
#         status = data.get("status")

#         order = db.course_orders.find_one({"paypad_reference": reference})

#         if order:
#             if status == "success":
#                 db.course_orders.update_one({"_id": order["_id"]}, {"$set": {"payment_status": "paid"}})
#                 return JsonResponse({"message": "Payment successful"}, status=200)
#             else:
#                 db.course_orders.update_one({"_id": order["_id"]}, {"$set": {"payment_status": "failed"}})
#                 return JsonResponse({"message": "Payment failed"}, status=400)

#     return JsonResponse({"error": "Invalid request"}, status=400)

class Courses(APIView):
    # permission_classes = [IsAuthenticated]
    def get(self, request):
        db = get_mongo_db()
        courses = list(db.courses.find())
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

logging.basicConfig(level=logging.DEBUG)

class CourseDetail(APIView):

    def get_object(self, pk: str):
        db = get_mongo_db()
        try:
            course = db.courses.find_one({"_id": ObjectId(pk)})
            if course:
                return course
            else:
                logging.error(f"No course found with id: {pk}")
                return None
        except PyMongoError as e:
            logging.error(f"Database error: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None

    def get(self, request, pk: str):
        logging.debug(f"Attempting to retrieve course with id: {pk}")
        course = self.get_object(pk)
        if course:
            serializer = CourseSerializer(course)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk: str):
        logging.debug(f"Attempting to update course with id: {pk}")
        course = self.get_object(pk)
        if course:
            serializer = CourseSerializer(instance=course, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk: str):
        logging.debug(f"Attempting to delete course with id: {pk}")
        db = get_mongo_db()
        course = self.get_object(pk)
        if course:
            db.courses.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)
    
class CourseLibraryView(APIView):
    def get(self, request):
        db = get_mongo_db()
        course_libraries = list(db.course_library.find())
        serializer = CourseLibrarySerializer(course_libraries, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CourseLibrarySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CourseLibraryDetailView(APIView):

    def get_object(self, pk: str):
        db = get_mongo_db()
        try:
            course_library = db.course_library.find_one({"_id": ObjectId(pk)})
            if course_library:
                return course_library
            else:
                logging.error(f"No course library found with id: {pk}")
                return None
        except PyMongoError as e:
            logging.error(f"Database error: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None

    def get(self, request, pk: str):
        logging.debug(f"Attempting to retrieve course library with id: {pk}")
        course_library = self.get_object(pk)
        if course_library:
            serializer = CourseLibrarySerializer(course_library)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk: str):
        logging.debug(f"Attempting to update course library with id: {pk}")
        course_library = self.get_object(pk)
        if course_library:
            serializer = CourseLibrarySerializer(instance=course_library, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk: str):
        logging.debug(f"Attempting to delete course library with id: {pk}")
        db = get_mongo_db()
        course_library = self.get_object(pk)
        if course_library:
            db.course_library.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Course library deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class Categories(APIView):

    def get(self, request):
        db = get_mongo_db()
        categories = list(db.categories.find())
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CoursesByCategory(APIView):
    def get(self, request, pk):
        db = get_mongo_db()
        try:
            category = db.categories.find_one({"_id": ObjectId(pk)})
            if category:
                courses = list(db.courses.find({"category_id": str(category['_id'])}))
                serializer = CourseSerializer(courses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_404_NOT_FOUND)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

# class CourseOrderAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         db = get_mongo_db()
#         orders = list(db.course_orders.find({"user_id": str(request.user.id)}))
#         serializer = CourseOrderSerializer(orders, many=True)
#         return Response(serializer.data)

#     def post(self, request):
#         db = get_mongo_db()
#         course_ids = request.data.get('course_ids', [])

#         if not course_ids:
#             return Response({"error": "No courses selected"}, status=status.HTTP_400_BAD_REQUEST)

#         total_price = 0
#         order_data = {
#             "user_id": str(request.user.id),
#             "total_price": 0,
#             "payment_status": "pending",
#             "created_at": datetime.utcnow(),
#             "updated_at": datetime.utcnow(),
#             "order_items": []
#         }
#         order_result = db.course_orders.insert_one(order_data)
#         order_id = str(order_result.inserted_id)

#         order_item_data = []
#         for course_id in course_ids:
#             course = db.courses.find_one({"_id": ObjectId(course_id)})
#             if course:
#                 total_price += course.get('price', 0)
#                 item_data = {
#                     "order_id": order_id,
#                     "course_id": course_id,
#                     "price": course.get('price', 0)
#                 }
#                 order_item_data.append(item_data)

#         if order_item_data:
#             db.course_order_items.insert_many(order_item_data)
#             db.course_orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"total_price": total_price}})

#         order = db.course_orders.find_one({"_id": ObjectId(order_id)})
#         serializer = CourseOrderSerializer(order)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)

# class CourseOrderDetailAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, order_id):
#         db = get_mongo_db()
#         order = db.course_orders.find_one({"_id": ObjectId(order_id), "user_id": str(request.user.id)})
#         if order:
#             serializer = CourseOrderSerializer(order)
#             return Response(serializer.data)
#         return Response(status=status.HTTP_404_NOT_FOUND)

# class CourseOrderItemAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, order_id):
#         db = get_mongo_db()
#         items = list(db.course_order_items.find({"order_id": order_id}))
#         serializer = CourseOrderItemSerializer(items, many=True)
#         return Response(serializer.data)

logger = logging.getLogger(__name__)

class Assignment(APIView):
    """
    API endpoint for Assignment operations (GET and POST).
    """

    def get(self, request):
        db = get_mongo_db()
        assignments = list(db.make_assignments.find())
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """
        Handles POST requests to create a new Assignment document in MongoDB.
        """
        serializer = AssignmentSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # This calls the create() method defined in your AssignmentSerializer
                assignment_instance = serializer.save() 
                
                # Use a new serializer instance with the created object
                # to ensure to_representation is called for the full response,
                # including embedded 'teacher' data.
                response_serializer = AssignmentSerializer(instance=assignment_instance)
                
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                # Log the exception for debugging purposes
                logger.exception("Error creating assignment in MongoDB via API.")
                
                # Return a 500 Internal Server Error for database-related issues
                return Response(
                    {"detail": f"An internal server error occurred while creating the assignment: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # If validation fails, return 400 Bad Request with serializer errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignmentDetail(APIView):
    def get_object(self, pk: str):
        db = get_mongo_db()
        try:
            assignments = db.make_assignments.find_one({"_id": ObjectId(pk)})
            if assignments:
                return assignments
            else:
                logging.error(f"No assignments found with id: {pk}")
                return None
        except PyMongoError as e:
            logging.error(f"Database error: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None

    def get(self, request, pk: str):
        assignment = self.get_object(pk)
        if assignment:
            serializer = AssignmentSerializer(assignment)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        assignment = self.get_object(pk)
        if assignment:
            serializer = AssignmentSerializer(instance=assignment, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        assignment = self.get_object(pk)
        if assignment:
            db.make_assignments.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Assignment deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

logger = logging.getLogger(__name__)



class AssignmentByCourse(APIView):
    def get(self, request, course_id):
        db = get_mongo_db()
        try:
            # 1. Validate the course_id and convert it to ObjectId
            course_oid = ObjectId(course_id)

            # 2. Fetch assignments for the given course_id by querying the embedded 'course.id' field
            #    This is the core of querying assignments by course_id
            assignments = list(db.make_assignments.find({"course.id": course_oid}))

            if not assignments:
                return Response({"detail": "No assignments found for this course."}, status=status.HTTP_404_NOT_FOUND)

            serializer = AssignmentSerializer(assignments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except InvalidId:
            logger.error(f"Invalid course ID format: {course_id}")
            return Response({"detail": "Invalid course ID format."}, status=status.HTTP_400_BAD_REQUEST)
        
class AssignmentSubmission(APIView):
    def get(self, request):
        db = get_mongo_db()
        submissions = list(db.submissions.find())
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssignmentSubmissionDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.submissions.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        submission = self.get_object(pk)
        if submission:
            serializer = SubmissionSerializer(submission)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        submission = self.get_object(pk)
        if submission:
            serializer = SubmissionSerializer(instance=submission, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        submission = self.get_object(pk)
        if submission:
            db.submissions.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Assignment submission deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class AssignmentSubmissionByUser(APIView):
    def get(self, request, user_id): # Changed 'pk' to 'user_id' for clarity
        db = get_mongo_db()
        submissions = list(db.submissions.find({"user_id": user_id})) # Assuming 'user_id' field in submissions
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

class Module(APIView):
    def get(self, request):
        db = get_mongo_db()
        modules = list(db.modules.find())
        serializer = ModuleInCourseSerializer(modules, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ModuleInCourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ModuleByCourse(APIView):
    def get(self, request, course_id):
        db = get_mongo_db()
        modules = list(db.modules.find({"course_id": course_id}))
        serializer = ModuleInCourseSerializer(modules, many=True)
        return Response(serializer.data)

class ModuleDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.modules.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        module = self.get_object(pk)
        if module:
            serializer = ModuleInCourseSerializer(module)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        module = self.get_object(pk)
        if module:
            serializer = ModuleInCourseSerializer(instance=module, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        module = self.get_object(pk)
        if module:
            db.modules.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Module deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)

class Video(APIView):
    def get(self, request):
        db = get_mongo_db()
        videos = list(db.videos.find())
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VideoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VideoByModule(APIView):
    def get(self, request, module_id):
        db = get_mongo_db()
        videos = list(db.videos.find({"module_id": module_id}))
        serializer = VideoSerializer(videos, many=True)
        return Response(serializer.data)


class VideoDetail(APIView):
    def get_object(self, pk):
        db = get_mongo_db()
        try:
            return db.videos.find_one({"_id": ObjectId(pk)})
        except:
            return None

    def get(self, request, pk):
        video = self.get_object(pk)
        if video:
            serializer = VideoSerializer(video)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        video = self.get_object(pk)
        if video:
            serializer = VideoSerializer(instance=video, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        db = get_mongo_db()
        video = self.get_object(pk)
        if video:
            db.videos.delete_one({"_id": ObjectId(pk)})
            return Response({'message': 'Video deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)
    


class CreateLiveClassView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a new live class and notify enrolled students"""
        serializer = LiveClassSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            db = get_mongo_db()
            data = serializer.validated_data
            
            # Validate course exists
            course_id = data['course_id']
            course = db.courses.find_one(
                {'_id': ObjectId(course_id)},
                {'name': 1, 'title': 1}  # Get course details for notification
            )
            if not course:
                return Response(
                    {"error": "Course not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate teacher exists
            teacher_id = data['teacher_id']
            teacher = db.teacherprofiles.find_one(
                {'_id': ObjectId(teacher_id)},
                {'name': 1, 'user_id': 1}
            )
            if not teacher:
                return Response(
                    {"error": "Teacher not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Prepare live class document
            live_class_data = {
                **data,
                'created_by': str(request.user.id),
                'created_at': datetime.now(pytz.utc),
                'status': 'scheduled',
                'participants': []
            }
            
            # Create the live class
            result = db.liveclasss.insert_one(live_class_data)
            live_class_id = str(result.inserted_id)

            # Get the created live class
            created_class = db.liveclasss.find_one({'_id': ObjectId(live_class_id)})
            
            # Send notifications to students enrolled in this course
            self.notify_enrolled_students(course_id, created_class, course, teacher)
            
            # Convert ObjectId to string for response
            created_class['_id'] = str(created_class['_id'])
            created_class['course_id'] = str(created_class['course_id'])
            created_class['teacher_id'] = str(created_class['teacher_id'])
            
            return Response(
                {
                    "message": "Live class created successfully",
                    "data": LiveClassSerializer(created_class).data
                }, 
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to create live class: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def notify_enrolled_students(self, course_id, live_class, course, teacher):
        """Notify all students who have this course in their user data"""
        db = get_mongo_db()
        channel_layer = get_channel_layer()

        # Find all users who have this course_id in their course array
        enrolled_students = db.users.find({
            'course._id': ObjectId(course_id)  # Match course._id in the array
        }, {'_id': 1, 'username': 1, 'email': 1})  # Get user details

        course_name = course.get('name') or course.get('title', 'Unknown Course')
        teacher_name = teacher.get('name', 'Unknown Teacher')

        student_count = 0
        for student in enrolled_students:
            student_id = str(student['_id'])
            student_count += 1

            # Send WebSocket notification
            async_to_sync(channel_layer.group_send)(
                f"user_{student_id}",
                {
                    "type": "send_notification",
                    "message": f"New live class: {live_class.get('title', 'Untitled')} for {course_name}",
                    "timestamp": datetime.now(pytz.utc).isoformat(),
                    "data": {
                        "live_class_id": str(live_class['_id']),
                        "course_id": course_id,
                        "course_name": course_name,
                        "teacher_name": teacher_name,
                        "title": live_class.get('title', ''),
                        "start_time": live_class.get('start_time'),
                        "action_url": f"/live-class/{str(live_class['_id'])}/join",
                        "notification_type": "live_class_scheduled"
                    }
                }
            )

            print(f"📨 Notification sent to student {student['username']} ({student_id}) for course {course_name}")

        # Also send to course-specific group for any connected clients
        async_to_sync(channel_layer.group_send)(
            f"liveclass_{course_id}",
            {
                "type": "liveclass_notification",
                "message": f"New live class scheduled: {live_class.get('title', 'Untitled')}",
                "class_id": str(live_class['_id']),
                "course_id": course_id,
                "course_name": course_name,
                "start_time": live_class.get('start_time').isoformat() if live_class.get('start_time') else None,
                "join_url": f"/live-class/{str(live_class['_id'])}/join"
            }
        )
    
        print(f"✅ Notified {student_count} students for course {course_name}")

    def get(self, request):
        """List all live classes"""
        try:
            db = get_mongo_db()
            
            # Build query based on request parameters
            query = {}
            if teacher_id := request.query_params.get('teacher_id'):
                if ObjectId.is_valid(teacher_id):
                    query['teacher_id'] = ObjectId(teacher_id)
            
            if course_id := request.query_params.get('course_id'):
                if ObjectId.is_valid(course_id):
                    query['course_id'] = ObjectId(course_id)
            
            if status := request.query_params.get('status'):
                query['status'] = status
            
            live_classes = list(db.liveclasss.find(query).sort('created_at', -1).limit(100))
            
            # Convert ObjectId to string for serialization
            for lc in live_classes:
                lc['_id'] = str(lc['_id'])
                if 'course_id' in lc:
                    lc['course_id'] = str(lc['course_id'])
                if 'teacher_id' in lc:
                    lc['teacher_id'] = str(lc['teacher_id'])
            
            serializer = LiveClassSerializer(live_classes, many=True)
            
            return Response({
                "count": len(live_classes),
                "results": serializer.data
            })
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch live classes: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            


class LiveClassDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, live_class_id):
        """Retrieve a single live class details"""
        try:
            if not ObjectId.is_valid(live_class_id):
                return Response(
                    {"error": "Invalid live class ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            db = get_mongo_db()
            live_class = db.liveclasss.find_one({'_id': ObjectId(live_class_id)})
            
            if not live_class:
                return Response(
                    {"error": "Live class not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(LiveClassSerializer(live_class).data)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, live_class_id):
        """Update a live class (partial update)"""
        try:
            if not ObjectId.is_valid(live_class_id):
                return Response(
                    {"error": "Invalid live class ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            db = get_mongo_db()
            live_class = db.liveclasss.find_one({'_id': ObjectId(live_class_id)})
            
            if not live_class:
                return Response(
                    {"error": "Live class not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = LiveClassSerializer(
                instance=live_class,
                data=request.data,
                partial=True
            )
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            
            return Response({
                "message": "Live class updated successfully",
                "data": serializer.data
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, live_class_id):
        """Cancel a live class"""
        try:
            if not ObjectId.is_valid(live_class_id):
                return Response(
                    {"error": "Invalid live class ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            db = get_mongo_db()
            result = db.liveclasss.update_one(
                {'_id': ObjectId(live_class_id)},
                {'$set': {'status': 'cancelled'}}
            )
            
            if result.modified_count == 0:
                return Response(
                    {"error": "Live class not found or already cancelled"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(
                {"message": "Live class cancelled successfully"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    
class TrackVideoProgressView(APIView):
    def post(self, request, user_id, video_id):
        try:
            user_oid = ObjectId(user_id)
            video_oid = ObjectId(video_id)
            data = json.loads(request.body.decode('utf-8'))
            current_time = data.get('currentTime', 0)

            db = get_mongo_db()
            # Update user's progress for this video in your database
            db.user_video_progress.update_one(
                {"user_id": user_oid, "video_id": video_oid},
                {"$set": {"last_watched_time": current_time}},
                upsert=True
            )

            # Get video duration (you might store this in your video document)
            video = db.videos.find_one({"_id": video_oid}, {"duration": 1})
            if video and video.get('duration'):
                duration_parts = video['duration'].split(':')
                total_seconds = int(duration_parts[0]) * 3600 + int(duration_parts[1]) * 60 + int(duration_parts[2])
                completion_threshold = 0.95
                if current_time / total_seconds >= completion_threshold:
                    # Mark video as completed for the user
                    db.user_video_progress.update_one(
                        {"user_id": user_oid, "video_id": video_oid},
                        {"$set": {"completed": True}}
                    )
                    return Response({"message": "Video marked as completed"}, status=200)

            return Response({"message": "Progress tracked"}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    
class CourseProgressDetailView(APIView):
    def get(self, request, user_id, course_id):
        db = get_mongo_db()

        try:
            user_oid = ObjectId(user_id)
            course_oid = ObjectId(course_id)
        except Exception:
            return Response({"error": "Invalid user_id or course_id"}, status=400)

        user = db.customusers.find_one({"_id": user_oid})
        course = db.courses.find_one({"_id": course_oid})

        if not user or not course:
            return Response({"error": "User or course not found"}, status=404)

        # Fetch activity counts
        completed_videos_count = db.user_course_activity.count_documents(
            {"user_id": user_oid, "course_id": course_oid, "activity_type": "video_completed"}
        )
        opened_notes_count = db.user_course_activity.count_documents(
            {"user_id": user_oid, "course_id": course_oid, "activity_type": "note_opened"}
        )
        assignments_submitted_count = db.user_course_activity.count_documents(
            {"user_id": user_oid, "course_id": course_oid, "activity_type": "assignment_submitted"}
        )
        pdfs_viewed_count = db.user_course_activity.count_documents(
            {"user_id": user_oid, "course_id": course_oid, "activity_type": "pdf_viewed"}
        )

        # Get total counts from the course structure
        total_videos = 0
        total_notes = 0
        total_assignments = 0 # You'll need to define where this comes from in your Course model
        total_pdfs = 0 # You'll need to define where blog PDFs related to a course are tracked

        if course.get('curriculum'):
            for module in course['curriculum']:
                if module.get('video'):
                    total_videos += len(module['video'])
                if module.get('course_note'):
                    total_notes += 1 # Assuming one note per module for simplicity

        # You'll need a way to link blog PDFs to courses to get total_pdfs

        # Calculate overall progress (you might need to weigh these differently)
        total_progress_points = (completed_videos_count if total_videos > 0 else 0) + \
                                (opened_notes_count if total_notes > 0 else 0) + \
                                (assignments_submitted_count if total_assignments > 0 else 0) + \
                                (pdfs_viewed_count if total_pdfs > 0 else 0)

        total_possible_points = (total_videos if total_videos > 0 else 1) + \
                                (total_notes if total_notes > 0 else 1) + \
                                (total_assignments if total_assignments > 0 else 1) + \
                                (total_pdfs if total_pdfs > 0 else 1) # Avoid division by zero

        progress_percentage = int((total_progress_points / total_possible_points) * 100) if total_possible_points > 0 else 0

        response_data = {
            "user_id": str(user['_id']),
            "course_id": str(course['_id']),
            "course_name": course.get('name'),
            "progress_percentage": progress_percentage,
            "details": {
                "videos": {"completed": completed_videos_count, "total": total_videos},
                "course_notes": {"opened": opened_notes_count, "total": total_notes},
                "assignments": {"submitted": assignments_submitted_count, "total": total_assignments},
                "blog_pdfs": {"viewed": pdfs_viewed_count, "total": total_pdfs},
            }
        }

        # Serialize the response (create a specific serializer for this)
        return Response(response_data)





class EventAPIView(APIView):
    def get(self, request, id=None):
        db = get_mongo_db()
        if id:
            event = db.events.find_one({"_id": ObjectId(id)})
            if not event:
                return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = EventSerializer(event)
            return Response(serializer.data)
        else:
            events = list(db.events.find())
            serializer = EventSerializer(events, many=True)
            return Response(serializer.data)

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            created_event = serializer.save()
            return Response(EventSerializer(created_event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        db = get_mongo_db()
        event = db.events.find_one({"_id": ObjectId(id)})
        if not event:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = EventSerializer(event, data=request.data)
        if serializer.is_valid():
            updated_event = serializer.save()
            return Response(EventSerializer(updated_event).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        User = get_user_model()







class GenerateCertificatePDF(APIView):
    # Option 1: Explicitly set authentication_classes to an empty list
    # This means NO authentication schemes will be run for this view.
    authentication_classes = [] 
    
    # Option 2: Set permission_classes to AllowAny
    # This means ANY user (authenticated or unauthenticated/anonymous) can access this view.
    # AllowAny is usually sufficient if you just want to make it public.
    permission_classes = [AllowAny] 

    def get(self, request):
        # Since authentication is removed or permission is AllowAny,
        # request.user will be an AnonymousUser if no session cookie is present.
        # You should remove or adapt this check:
        # if not request.user.is_authenticated:
        #     return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        # If you remove the authentication, this check would always be false and return 401.

        # If you still need a name, but don't want to enforce authentication:
        # You could get a name from query params or assume an anonymous name
        participant_name = request.query_params.get('username', 'Participant Name') # Get name from query param
        if not participant_name: # Fallback if 'name' not provided
             participant_name = "Anonymous Participant"

        # If you *sometimes* want to use the authenticated user's name if available,
        # but don't require authentication, you can check:
        if request.user.is_authenticated:
            user = request.user
            # Fetch user data from MongoDB for the name
            client = MongoClient(settings.MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
            db = get_mongo_db()
            users_collection = db.customusers
            mongo_user = users_collection.find_one({"email": user.email})
            client.close()
            participant_name = mongo_user.get('first_name', '') + ' ' + mongo_user.get('last_name', '') if mongo_user and (mongo_user.get('first_name') or mongo_user.get('last_name')) else (mongo_user.get('email', 'N/A') if mongo_user else user.username)
        else:
            participant_name = request.query_params.get('name', 'Completed student') # Fallback if not authenticated


        # Get course name and completion date from query parameters
        course_name = request.query_params.get('course', 'Course Name Not Provided')
        completion_date_str = request.query_params.get('completion_date', 'Date Not Provided')

        try:
            # --- IMPORTANT ---
            # If you remove authentication, you CANNOT rely on request.user for the name.
            # You must get the participant_name from somewhere else, e.g., query parameters.
            # The current MongoDB user fetching logic relies on request.user.email.
            # If you still need a name from MongoDB for an *unauthenticated* request,
            # you would need to pass an identifier (like email or user ID) in the URL/body.

            # Example: If you pass user_id in query params for unauthenticated certificate
            # user_id_from_param = request.query_params.get('user_id')
            # if user_id_from_param:
            #     try:
            #         client = MongoClient(settings.MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
            #         db = get_mongo_db()
            #         users_collection = db.customusers
            #         mongo_user = users_collection.find_one({"_id": ObjectId(user_id_from_param)})
            #         client.close()
            #         if mongo_user:
            #             participant_name = mongo_user.get('username')
            #             if not participant_name.strip(): # Fallback if first/last name empty
            #                  participant_name = mongo_user.get('email', 'N/A')
            #         else:
            #             logger.warning(f"User with ID {user_id_from_param} not found in MongoDB for certificate.")
            #             participant_name = "Unknown Participant" # Default if ID not found
            #     except Exception as e:
            #         logger.error(f"Error fetching MongoDB user for certificate with ID {user_id_from_param}: {e}")
            #         participant_name = "Error Fetching Name" # Default if MongoDB fetch fails
            # else:
            #     participant_name = request.query_params.get('name', 'Participant Name') # Default if no user_id

            # Load the PDF template
            template_path = "staticfiles/certificate/COC.pdf"  # Update this path
            with open(template_path, "rb") as template_file:
                pdf_reader = PdfReader(template_file)
                pdf_writer = PdfWriter()

                # Use the first page of the template
                page = pdf_reader.pages[0]
                pdf_writer.add_page(page)

                # Create a temporary file to overlay text
                overlay = io.BytesIO()
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Calibri", style="", fname=settings.STATIC_ROOT + "/fonts/calibri.ttf", uni=True)
                pdf.add_font("Calibri", style="B", fname=settings.STATIC_ROOT + "/fonts/calibri.ttf", uni=True)
                pdf.add_font("Calibri", style="I", fname=settings.STATIC_ROOT + "/fonts/calibri.ttf", uni=True)
                pdf.add_font("Calibri", style="BI", fname=settings.STATIC_ROOT + "/fonts/calibri.ttf", uni=True)

                # Set font and positions for text overlay
                pdf.set_font("Calibri", size=24, style='B')
                pdf.set_xy(60, 100)  # Adjust these coordinates based on your template
                pdf.cell(0, 10, participant_name, align='C')

                pdf.set_font("Calibri", size=20, style='I')
                pdf.set_xy(60, 125)  # Adjust these coordinates based on your template
                pdf.cell(0, 10, course_name, align='C')

                pdf.set_font("Calibri", size=20)
                pdf.set_xy(60, 150)  # Adjust these coordinates based on your template
                pdf.cell(0, 10, completion_date_str, align='C')

                # Output the overlay to a buffer
                pdf.output(overlay)
                overlay.seek(0)

                # Merge the overlay with the template
                overlay_pdf = PdfReader(overlay)
                page.merge_page(overlay_pdf.pages[0])

                # Write the final PDF to a buffer
                output_buffer = io.BytesIO()
                pdf_writer.write(output_buffer)

                # Create a response with the PDF data
                response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="Completion Certificate - {participant_name}.pdf"'
                return response

        except Exception as e:
            logger.error(f"Error generating certificate: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

logger = logging.getLogger(__name__)

# Brevo configuration
BREVO_API_KEY = os.getenv('Brevo_API')

# Map courses to Brevo list IDs
COURSE_LISTS = {
    "AML/KYC Compliance": {
        "list_id": 7,  # Brevo contact list ID
        "template_id": 12,  # Brevo template ID or your custom template name
        "course_date": "24th August 2025, 07:00pm",
        "zoom_link": "https://zoom.us/j/95062242795?pwd=r2CTvBheLUQ0YC7Wr8jYwRQRs5PgeU.1"
    },
    "Data Analysis": {
        "list_id": 8,
        "template_id": 8,
        "course_date": "25th August 2025, 07:00pm",
        "zoom_link": "https://zoom.us/j/95062242796?pwd=differentpassword"
    },
    "Business Analysis & Project Management": {
        "list_id": 9,
        "template_id": 14,
        "course_date": "26th August 2025, 07:00pm",
        "zoom_link": "https://zoom.us/j/95062242797?pwd=anotherpassword"
    },
    "Cybersecurity": {
        "list_id": 10,
        "template_id": 13,
        "course_date": "27th August 2025, 07:00pm",
        "zoom_link": "https://zoom.us/j/95062242798?pwd=yetanotherpassword"
    }
}

def format_phone_number(phone):
    """Format phone number for Brevo compliance"""
    if not phone:
        return None
    # Remove all non-digit characters
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Add + if international number
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    return cleaned if cleaned else None

class EventRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EventRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Initialize Brevo API client
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = BREVO_API_KEY
            
            api_instance = ContactsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            data = serializer.validated_data
            course_name = data['course_name']
            formatted_phone = format_phone_number(data.get('phone_number'))

            course_settings = COURSE_LISTS.get(course_name, {})
            if not course_settings:
                return Response(
                    {"error": "Invalid course selection"},
                    status=status.HTTP_400_BAD_REQUEST
                )
             
            # Prepare contact attributes
            contact_attrs = {
                'FIRSTNAME': data['first_name'],
                'LASTNAME': data.get('last_name', ''),
            }
            
            # Only add phone if valid
            if formatted_phone:
                contact_attrs['SMS'] = formatted_phone
            
            # Create Brevo contact
            create_contact = CreateContact(
                email=data['email'],
                attributes=contact_attrs,
                list_ids=[course_settings['list_id']],
                update_enabled=True
            )
            
            # Try Brevo API first
            try:
                api_response = api_instance.create_contact(create_contact)
                brevo_success = True
                logger.info(f"Brevo contact created for {data['email']}")
            except ApiException as e:
                logger.error(f"Brevo API Error: {e.body if hasattr(e, 'body') else str(e)}")
                brevo_success = False
            
            # Save to MongoDB
            db = get_mongo_db()
            registration = {
                "course_name": course_name,
                "email": data['email'],
                "first_name": data['first_name'],
                "last_name": data.get('last_name', ''),
                "phone_number": data.get('phone_number'),
                "whatsapp_number": data.get('whatsapp_number'),
                "message": data.get('message', ''),
                "registration_date": datetime.now().isoformat(),
                "status": "registered",
                "brevo_synced": brevo_success,
                "brevo_formatted_phone": formatted_phone
            }
            
            result = db.registrations.insert_one(registration)

            # Send confirmation email via Celery
            send_course_registration_email.delay(
                to_email=data['email'],
                first_name=data['first_name'],
                course_name=course_name,
                template_id=course_settings['template_id'],
                course_date=course_settings['course_date'],
                zoom_link=course_settings['zoom_link'],
            )
            
            response = {
                "success": True,
                "message": "Registration complete. Confirmation email sent.",
                "registration_id": str(result.inserted_id),
                "course": course_name,
                "brevo_synced": brevo_success
            }
            
            if not brevo_success:
                response["warning"] = "Registered but failed to sync with mailing list"
            
            return Response(response, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Registration process failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


logger = logging.getLogger(__name__)

# Brevo Configuration
BREVO_API_KEY = os.getenv('Brevo_API')

# Define course choices and their corresponding list IDs
COURSE_CHOICES = [
    ('AML/KYC Compliance', 'AML/KYC Compliance'),
    ('Business Analysis & Project Management', 'Business Analysis & Project Management'),
    ('Cybersecurity', 'Cybersecurity'),
    ('Data Analysis', 'Data Analysis'),
]

# Map courses to their Brevo list IDs (with and without message)
COURSE_LIST_MAPPING = {
    'AML/KYC Compliance': {
        'with_message': 16,    # Replace with actual list ID
        'without_message': 17,  # Replace with actual list ID
    },
    'Business Analysis & Project Management': {
        'with_message': 14,    # Replace with actual list ID
        'without_message': 15,  # Replace with actual list ID
    },
    'Cybersecurity': {
        'with_message': 18,    # Replace with actual list ID
        'without_message': 19,  # Replace with actual list ID
    },
    'Data Analysis': {
        'with_message': 20,    # Replace with actual list ID
        'without_message': 21,  # Replace with actual list ID
    },
}

class ConsultationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConsultationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Initialize Brevo API client
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = BREVO_API_KEY
            
            api_instance = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            data = serializer.validated_data
            has_message = bool(data.get('message', '').strip())
            selected_course = data.get('course')
            
            # Validate course selection
            if not selected_course or selected_course not in COURSE_LIST_MAPPING:
                return Response(
                    {"error": "Invalid course selection"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get appropriate list ID based on course and message presence
            list_mapping = COURSE_LIST_MAPPING[selected_course]
            list_id = list_mapping['with_message'] if has_message else list_mapping['without_message']
            
            # Prepare contact attributes - only include valid phone numbers
            contact_attrs = {
                'FIRSTNAME': data['firstName'],
                'LASTNAME': data.get('lastName', ''),
                'COURSE': selected_course,
            }
            
            # Only add phone numbers if they're in valid format
            phone_number = data.get('phone_number')
            if phone_number and re.match(r'^\+[1-9]\d{1,14}$', phone_number):
                contact_attrs['SMS'] = phone_number
            
            whatsapp_number = data.get('whatsappNumber')
            if whatsapp_number and re.match(r'^\+[1-9]\d{1,14}$', whatsapp_number):
                contact_attrs['WHATSAPP'] = whatsapp_number
            
            # Create Brevo contact
            create_contact = sib_api_v3_sdk.CreateContact(
                email=data['email'],
                attributes=contact_attrs,
                list_ids=[list_id],
                update_enabled=True
            )
            
            # Try Brevo API
            try:
                api_response = api_instance.create_contact(create_contact)
                brevo_success = True
                logger.info(f"Brevo contact created for {data['email']} in list {list_id}")
            except ApiException as e:
                logger.error(f"Brevo API Error: {e.body if hasattr(e, 'body') else str(e)}")
                brevo_success = False
                # If Brevo fails due to phone number, try without phone numbers
                if "phone" in str(e).lower() or "whatsapp" in str(e).lower():
                    try:
                        # Remove phone attributes and try again
                        if 'SMS' in contact_attrs:
                            del contact_attrs['SMS']
                        if 'WHATSAPP' in contact_attrs:
                            del contact_attrs['WHATSAPP']
                        
                        create_contact = sib_api_v3_sdk.CreateContact(
                            email=data['email'],
                            attributes=contact_attrs,
                            list_ids=[list_id],
                            update_enabled=True
                        )
                        api_response = api_instance.create_contact(create_contact)
                        brevo_success = True
                        logger.info(f"Brevo contact created without phone numbers for {data['email']}")
                    except ApiException as retry_e:
                        logger.error(f"Brevo API Retry Error: {retry_e.body if hasattr(retry_e, 'body') else str(retry_e)}")
                        brevo_success = False
            
            # Save to your database
            db = get_mongo_db()
            consultation = {
                "email": data['email'],
                "first_name": data['firstName'],
                "last_name": data.get('lastName', ''),
                "phone_number": data.get('phone_number', ''),
                "whatsapp_number": data.get('whatsappNumber', ''),
                "message": data.get('message', ''),
                "course": selected_course,
                "has_message": has_message,
                "created_at": datetime.now().isoformat(),
                "brevo_synced": brevo_success,
                "brevo_list_id": list_id,
            }
            
            result = db.consultations.insert_one(consultation)

            response = {
                "success": True,
                "message": "Consultation request submitted successfully",
                "consultation_id": str(result.inserted_id),
                "course": selected_course,
                "has_message": has_message,
                "brevo_synced": brevo_success
            }
            
            if not brevo_success:
                response["warning"] = "Consultation saved but failed to sync with mailing list"
            
            return Response(response, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Consultation submission failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Consultation submission process failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class SendTemplateToListAPIView(APIView):
    """
    API endpoint to send template ID 9 to all contacts in list ID 8
    """
    
    def post(self, request):
        """
        Send template to all contacts in the specified list
        """
        # Brevo API configuration
        brevo_api_key = settings.BREVO_API_KEY
        sender_email = settings.DEFAULT_FROM_EMAIL
        sender_name = "Titans Careers"
        list_id = 8  # Specific list ID
        template_id = 10  # Specific template ID
        
        # Get all contacts from the specified list
        contacts = self.get_brevo_contacts_in_list(brevo_api_key, list_id)
        
        if not contacts:
            return Response(
                {"error": f"No contacts found in list {list_id}"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Send email to each contact
        results = {
            "success_count": 0,
            "fail_count": 0,
            "failed_emails": [],
            "total_contacts": len(contacts),
            "list_id": list_id,
            "template_id": template_id
        }
        
        for contact in contacts:
            success = self.send_transactional_email(
                brevo_api_key,
                contact['email'],
                contact.get('firstname', ''),
                sender_email,
                sender_name,
                template_id,
                {
                    "firstname": contact.get('firstname', ''),
                    "course_date": "24th August 2025, 07:00pm",
                    "zoom_link": "https://zoom.us/j/95062242795?pwd=r2CTvBheLUQ0YC7Wr8jYwRQRs5PgeU.1"
                }
            )
            
            if success:
                results["success_count"] += 1
            else:
                results["fail_count"] += 1
                results["failed_emails"].append(contact['email'])
        
        return Response(results, status=status.HTTP_200_OK)

    def get_brevo_contacts_in_list(self, api_key, list_id):
        """
        Retrieve all contacts from specific Brevo list with pagination handling
        """
        url = f"https://api.brevo.com/v3/contacts/lists/{list_id}/contacts"
        limit = 100  # Brevo's default limit
        offset = 0
        all_contacts = []
        
        headers = {
            "accept": "application/json",
            "api-key": api_key
        }
        
        try:
            while True:
                # Add pagination parameters
                params = {
                    "limit": limit,
                    "offset": offset
                }
                
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                contacts = data.get('contacts', [])
                if not contacts:
                    break
                
                for contact in contacts:
                    if contact.get('email'):
                        all_contacts.append({
                            'email': contact['email'],
                            'firstname': contact.get('attributes', {}).get('FIRSTNAME', ''),
                            'lastname': contact.get('attributes', {}).get('LASTNAME', '')
                        })
                
                # Check if we've fetched all contacts
                if len(contacts) < limit:
                    break
                    
                offset += limit
                
            return all_contacts
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching contacts from list {list_id}: {e}")
            return None

    def send_transactional_email(self, api_key, to_email, to_name, sender_email, sender_name, template_id, params):
        """
        Send transactional email using Brevo template
        """
        url = "https://api.brevo.com/v3/smtp/email"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        payload = {
            "templateId": template_id,
            "to": [{"email": to_email, "name": to_name}],
            "params": params,
            "sender": {"email": sender_email, "name": sender_name}
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error sending email to {to_email}: {e}")
            return False