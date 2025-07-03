# views.py

from django.shortcuts import render
from rest_framework import status

from blog.models import BlogUser
from blog.serializer import BlogUserSerializer
from .serializer import CourseProgressSerializer, CustomUserSerializer, TeacherProfileSerializer, NotificationSerializer, CourseProgressRecordSerializer, CourseProgressResponseSerializer
from rest_framework_simplejwt.views import TokenObtainPairView # Use this for base JWT view
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseRedirect
from courses.mongo_utils import get_mongo_db
from bson import ObjectId
from django.contrib.auth import logout
from google.oauth2 import id_token
from django.contrib.auth import authenticate, login
from google.auth.transport import requests
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
import jwt
from datetime import datetime, timedelta
import datetime
from django.conf import settings
import os
import logging
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import CustomUser
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import TokenRefreshView
from .serializer import CustomTokenObtainPairSerializer # Import your custom serializer
from rest_framework_simplejwt.tokens import RefreshToken
from .utils.token_utils import create_jwt_tokens
from bson.json_util import default as bson_default
from sib_api_v3_sdk.rest import ApiException
import sib_api_v3_sdk as brevo_sdk
from rest_framework import serializers
from rest_framework import permissions


db = get_mongo_db()
users_collection = db['customusers']

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("Received Google login request")
        token = request.data.get('token')

        if not token:
            logger.error("Token is missing from the request")
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv('CLIENT_ID'))
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            extracted_user_info = {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'name': idinfo.get('name', ''),
                'profile_picture': idinfo.get('picture', ''),
                'last_login': datetime.utcnow(),
                'role': 'STUDENT', # Default role for new users
                'username': idinfo.get('email', '').split('@')[0],
                'phone_number': '',
                'course': [],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'date_joined': datetime.utcnow(),
            }

            db = get_mongo_db()
            users_collection = db['customusers']

            user_document = users_collection.find_one({'google_id': idinfo['sub']})

            if not user_document:
                logger.info(f"Creating new user: {extracted_user_info['email']}")
                if '_id' in extracted_user_info:
                    del extracted_user_info['_id']

                inserted_result = users_collection.insert_one(extracted_user_info)
                user_document = users_collection.find_one({'_id': inserted_result.inserted_id})
            else:
                logger.info(f"User already exists: {extracted_user_info['email']}")
                users_collection.update_one(
                    {'google_id': idinfo['sub']},
                    {'$set': {
                        'last_login': datetime.utcnow(),
                        'email': extracted_user_info['email'],
                        'first_name': extracted_user_info['first_name'],
                        'last_name': extracted_user_info['last_name'],
                        'name': extracted_user_info['name'],
                        'profile_picture': extracted_user_info['profile_picture'],
                    }}
                )
                user_document = users_collection.find_one({'google_id': idinfo['sub']})


            # --- Session Handling (with added logging) ---
            logger.debug(f"Before session assignment. Session ID: {request.session.session_key}, Session data: {request.session.items()}")

            request.session['user_id'] = str(user_document['_id'])
            request.session.modified = True

            logger.info(f"Session 'user_id' set to: {request.session['user_id']}")
            logger.info(f"Session marked as modified. New Session ID (if generated/updated): {request.session.session_key}")
            logger.debug(f"After session assignment. Full Session data: {request.session.items()}")
            # --- End Session Handling ---

            logger.info(f"Successfully logged in user: {user_document['email']}")

            serializer = CustomUserSerializer(user_document)

            return Response({
                'message': 'Login successful',
                'user': serializer.data,
                'session_key': request.session.session_key # Include session key in response
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Error verifying Google token: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return Response({'error': 'An unexpected error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


import logging
logger = logging.getLogger(__name__)


class Signup(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):

            email = serializer.validated_data['email']
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')
            role = serializer.validated_data.get('role', 'STUDENT')
            phone_number = serializer.validated_data.get('phone_number', '')
            profile_pic = serializer.validated_data.get('profile_pic', '')
            courses_data = serializer.validated_data.get('course', [])

            db = get_mongo_db()
            users_collection = db.customusers

            hashed_password = make_password(password)

            processed_courses = []
            for c in courses_data:
                if 'id' in c and ObjectId.is_valid(c['id']):
                    c['id'] = ObjectId(c['id'])
                processed_courses.append(c)

            user_data_for_mongo = {
                "email": email,
                "username": username,
                "password": hashed_password,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "phone_number": phone_number,
                "profile_pic": profile_pic,
                "course": processed_courses,
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "date_joined": timezone.now(),
                "last_login": None,
            }

            result = users_collection.insert_one(user_data_for_mongo)
            mongo_id = str(result.inserted_id)

            # Return relevant user data
            created_user_mongo_doc = users_collection.find_one({"_id": result.inserted_id})
            response_serializer = CustomUserSerializer(created_user_mongo_doc)
            return Response({"user": response_serializer.data, "message": "User registered successfully"}, status=status.HTTP_201_CREATED)

logger = logging.getLogger(__name__)

class Login(APIView): # This view will now handle student login with JWT
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        # The authenticate call will use your MongoAuthBackend
        user = authenticate(request=request, email=email, password=password)

        if user is not None:
            if user.is_active:
                db = get_mongo_db()
                serializer_class = None
                collection_name = None
                message = "Logged in successfully"

                # Determine which serializer to use and which collection to update
                if isinstance(user, CustomUser):
                    serializer_class = CustomUserSerializer
                    collection_name = 'customusers'
                    message = "Student logged in successfully"
                elif isinstance(user, BlogUser):
                    serializer_class = BlogUserSerializer
                    collection_name = 'bloguser'
                    message = "Blogger logged in successfully" # BlogUser can only be 'BLOGGER' now
                else:
                    logger.error(f"UnifiedLogin: Unknown user type returned by backend for user_id: {user.id}")
                    return Response({"error": "An internal error occurred (unknown user type)."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                if serializer_class is None:
                     return Response({"error": "Could not determine user type for serialization."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Update last_login in the correct MongoDB collection
                db[collection_name].update_one(
                    {"_id": user._mongo_doc['_id']},
                    {"$set": {"last_login": timezone.now()}}
                )
                
                # Re-fetch the updated document for the response, including updated last_login
                updated_user_document = db[collection_name].find_one({"_id": user._mongo_doc['_id']})

                serializer = serializer_class(updated_user_document)

                tokens = create_jwt_tokens(user)

                return Response({
                    "access": tokens['access'],
                    "refresh": tokens['refresh'],
                    "user_info": serializer.data,
                    "message": message
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "User account is inactive."}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"error": "Invalid credentials. Please check your email and password."}, status=status.HTTP_400_BAD_REQUEST)



class Logout(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)


class TeacherLoginView(TokenObtainPairView):
    """
    Custom login view for teachers.
    Handles authentication and custom data fetching/validation.
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            # This calls CustomTokenObtainPairSerializer.validate(),
            # which in turn calls super().validate() to authenticate the user
            # and generate tokens. It also populates serializer.user.
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.warning(f"Login failed during serializer validation: {e.detail if hasattr(e, 'detail') else e}")
            # Re-raise or return a specific error response
            return Response(e.detail if hasattr(e, 'detail') else {"detail": "Authentication failed."}, status=status.HTTP_401_UNAUTHORIZED)
            # You might want to customize the error messages here

        user = serializer.user # This is your CustomUser instance, should have _mongo_doc

        # --- DEBUG LOGGING for _mongo_doc state in View ---
        logger.debug(
            f"DEBUG (TeacherLoginView.post): Authenticated user: {user.email}, "
            f"hasattr(_mongo_doc): {hasattr(user, '_mongo_doc')}, "
            f"_mongo_doc is None: {user._mongo_doc is None if hasattr(user, '_mongo_doc') else 'N/A'}, "
            f"keys: {list(user._mongo_doc.keys()) if hasattr(user, '_mongo_doc') and user._mongo_doc else 'N/A'}"
        )
        # --- END DEBUG LOGGING ---


        if not hasattr(user, '_mongo_doc') or not user._mongo_doc:
            logger.error(f"User {user.email} authenticated but _mongo_doc is missing or empty. Internal error.")
            return Response(
                {"non_field_errors": [_('User data not found in MongoDB after authentication. (Internal error)')]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        teacher_mongo_doc = user._mongo_doc

        # --- Role Check (now in the view) ---
        if teacher_mongo_doc.get('role') != 'TEACHER':
            logger.warning(f"User {user.email} attempted teacher login but is not a TEACHER. Role: {teacher_mongo_doc.get('role')}")
            return Response(
                {"detail": _('Only teachers can log in via this endpoint.')},
                status=status.HTTP_403_FORBIDDEN
    )


        # teacher_profile_data = {}
        # teacher_profiles_collection = db['teacherprofiles']

        # if teacher_profiles_collection:
        #     try:
        #         # Use the _id from the customusers document to link to teacherprofiles
        #         teacher_profile_data = teacher_profiles_collection.find_one({'user_id': mongo_doc.get('_id')})

        #         if not teacher_profile_data:
        #             logger.warning(f"Teacher profile not found in 'teacherprofiles' for user {user.email} (ID: {mongo_doc.get('_id')}).")
        #             # Decide if a missing profile is a hard error or just omit data
        #             # return Response({"detail": _('Teacher profile not found.')}, status=status.HTTP_404_NOT_FOUND)
        #         else:
        #             logger.debug(f"Fetched teacher profile for {user.email}.")

        #     except Exception as e:
        #         logger.error(f"Error fetching teacher profile for user {user.email}: {e}", exc_info=True)
        #         return Response(
        #             {"detail": _('Failed to load profile data due to an internal error.')},
        #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
        #         )

        # # --- Combine data for user_info ---
        # user_info_combined = {
        #     'id': str(mongo_doc.get('_id')),
        #     'email': mongo_doc.get('email'),
        #     'first_name': mongo_doc.get('first_name'),
        #     'last_name': mongo_doc.get('last_name'),
        #     'role': mongo_doc.get('role'),
        #     'bio': mongo_doc.get('bio'),
        #     'profile_picture': mongo_doc.get('profile_picture'),
        #     'phone_number': mongo_doc.get('phone_number'),
        #     # Add any other core user fields from customusers
        # }

        # # Add/override with data from teacherprofiles
        # if teacher_profile_data:
        #     user_info_combined['special_certifications'] = teacher_profile_data.get('special_certifications', [])
        #     user_info_combined['availability_schedule'] = teacher_profile_data.get('availability_schedule', {})
        #     user_info_combined['years_experience'] = teacher_profile_data.get('years_experience')
        #     # Add more fields from teacherprofiles as needed

        # # Validate the combined user_info using UserInfoSerializer
        # user_info_serializer = TeacherProfileSerializer(user_info_combined)
        
        # Prepare the final response data
        teacher_info_serializer = TeacherProfileSerializer(teacher_mongo_doc)

# Prepare the final response data
        response_data = {
            'access': serializer.validated_data['access'],
            'refresh': serializer.validated_data['refresh'],
            'user_info': teacher_info_serializer.data, # Directly use the serialized teacher data
        }
        
        logger.info(f"Teacher {user.email} successfully logged in.")
        return Response(response_data, status=status.HTTP_200_OK)

class Teacher(APIView):
    def post(self, request):
        serializer = TeacherProfileSerializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.save()
            teacher_data = serializer.data
            teacher_data['id'] = str(teacher_data['id'])  # Ensure ObjectId is converted to string
            return Response({"Teacher": teacher_data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        db = get_mongo_db()
        teachers = db.teacherprofiles.find()
        serializer = TeacherProfileSerializer([teacher for teacher in teachers], many=True)
        return Response(serializer.data)
    
class Student(APIView):
    def get(self, request):
        db = get_mongo_db()
        students = db.customusers.find()
        serializer = CustomUserSerializer([student for student in students], many=True)
        return Response(serializer.data)
    
class StudentDetail(APIView):
    def get(self, request, pk):
        db = get_mongo_db()
        student = db.customusers.find_one({"_id": ObjectId(pk)})
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomUserSerializer(student)
        return Response(serializer.data)

    def put(self, request, student_id):
        db = get_mongo_db()
        student = db.customusers.find_one({"_id": ObjectId(student_id)})
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomUserSerializer(student, data=request.data)
        if serializer.is_valid():
            updated_student = serializer.save()
            return Response({"student": updated_student}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  

class StudentFilterByCourse(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, format=None):
        query = {"role": "STUDENT"}

        if not course_id:
            return Response(
                {"error": "Course ID must be provided in the URL path."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not ObjectId.is_valid(course_id):
            return Response(
                {"error": "Invalid 'course_id' format. Must be a valid MongoDB ObjectId string."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Construct the query using the course_id from the URL path
        query["course._id"] = ObjectId(course_id)
        logger.info(f"Filtering students by course_id: {course_id}")

        db = get_mongo_db()

        try:
            # Fetch the students
            students_cursor = db.customusers.find(query)
            students_list = list(students_cursor)

            # Get the total count
            total_students_count = len(students_list)

            if not students_list:
                return Response(
                    {
                        "message": f"No students found in course with ID '{course_id}'.",
                        "students": [], # Return an empty list
                        "total_students": 0 # Explicitly return 0
                    },
                    status=status.HTTP_200_OK
                )

            serializer = CustomUserSerializer(students_list, many=True)

            # Return both the serialized data and the total count
            return Response({
                "students": serializer.data,
                "total_students": total_students_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error filtering students by course: {e}", exc_info=True)
            return Response(
                {"error": "An internal server error occurred while filtering students."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetCSRFToken(APIView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        csrf_token = get_token(request)
        response = JsonResponse({'message': 'CSRF token set.'})
        response['X-CSRFToken'] = csrf_token
        return response

class SendNotification(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        message = request.data.get('message')

        # Insert notification into MongoDB
        notification = {
            'user_id': ObjectId(user_id),
            'message': message,
            'is_read': False,
            'created_at': datetime.now()
        }
        db.Notification.insert_one(notification)

        # Send notification via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "send_notification",
                "message": message
            }
        )

        return Response({"message": "Notification sent successfully"}, status=status.HTTP_200_OK)
    
def social_callback(request):
    return HttpResponseRedirect("http://127.0.0.1:5503/course.html")


class UserCourseProgressView(APIView):
    # Consider adding permission_classes here, e.g., IsAuthenticated
    # permission_classes = [IsAuthenticated] # Add if only authenticated users can view/update their progress

    def get(self, request, user_id, course_id):
        db = get_mongo_db()

        try:
            user_oid = ObjectId(user_id)
            course_oid = ObjectId(course_id)
        except Exception:
            return Response({"error": "Invalid user_id or course_id"}, status=status.HTTP_400_BAD_REQUEST)

        user = db.customusers.find_one({"_id": user_oid})
        course = db.courses.find_one({"_id": course_oid})

        if not user or not course:
            return Response({"error": "User or course not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Calculate Progress (as you already do) ---
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

        total_videos = 0
        total_notes = 0
        total_assignments = db.assignments.count_documents({"course._id": course_oid})
        total_pdfs = db.course_library.count_documents({"course._id": course_oid, "file": {"$ne": None}, "url": {"$eq": None}})

        if course.get('curriculum'):
            for module in course['curriculum']:
                if module.get('video'):
                    total_videos += len(module['video'])
                if module.get('course_note'):
                    total_notes += 1

        total_progress_points = completed_videos_count + opened_notes_count + assignments_submitted_count + pdfs_viewed_count
        total_possible_points = total_videos + total_notes + total_assignments + total_pdfs

        progress_percentage = int((total_progress_points / total_possible_points) * 100) if total_possible_points > 0 else 0

        calculated_progress_data = {
            "user_id": str(user['_id']), # Store as string for the serializer
            "course_id": str(course['_id']), # Store as string for the serializer
            "progress_percentage": progress_percentage,
            "details": {
                "videos": {"completed": completed_videos_count, "total": total_videos},
                "course_notes": {"opened": opened_notes_count, "total": total_notes},
                "assignments": {"submitted": assignments_submitted_count, "total": total_assignments},
                "blog_pdfs": {"viewed": pdfs_viewed_count, "total": total_pdfs},
            },
            "last_updated": timezone.now() # Add timestamp
        }

        # --- Upsert into course_progress collection ---
        course_progress_collection = db.course_progress
        existing_progress = course_progress_collection.find_one(
            {"user_id": user_oid, "course_id": course_oid}
        )

        progress_serializer = CourseProgressSerializer(data=calculated_progress_data)
        progress_serializer.is_valid(raise_exception=True)

        if existing_progress:
            # Update existing document
            progress_instance = progress_serializer.update(existing_progress, progress_serializer.validated_data)
            logger.info(f"Updated course progress for user {user_id} in course {course_id}")
        else:
            # Create new document
            progress_instance = progress_serializer.create(progress_serializer.validated_data)
            logger.info(f"Created new course progress for user {user_id} in course {course_id}")

        # --- Prepare response for the client (same as before) ---
        details_list = []

        details_list.append({
            "type": "videos",
            "completed": completed_videos_count, # Keep all values here
            "opened": opened_notes_count,
            "submitted": assignments_submitted_count,
            "viewed": pdfs_viewed_count,
            "total": total_videos
        })
        details_list.append({
            "type": "course_notes",
            "completed": completed_videos_count, # Keep all values here
            "opened": opened_notes_count,
            "submitted": assignments_submitted_count,
            "viewed": pdfs_viewed_count,
            "total": total_notes
        })
        details_list.append({
            "type": "assignments",
            "completed": completed_videos_count, # Keep all values here
            "opened": opened_notes_count,
            "submitted": assignments_submitted_count,
            "viewed": pdfs_viewed_count,
            "total": total_assignments
        })
        details_list.append({
            "type": "blog_pdfs",
            "completed": completed_videos_count, # Keep all values here
            "opened": opened_notes_count,
            "submitted": assignments_submitted_count,
            "viewed": pdfs_viewed_count,
            "total": total_pdfs
        })

        response_data = {
            "user_id": str(user_oid),
            "course_id": str(course_oid),
            "course_name": course.get('name'),
            "progress_percentage": progress_percentage,
            "details": details_list,
        }

        # Use CourseProgressResponseSerializer for the final API response format
        final_response_serializer = CourseProgressResponseSerializer(data=response_data)
        if final_response_serializer.is_valid():
            return Response(final_response_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Error serializing final response for user {user_id} course {course_id}: {final_response_serializer.errors}")
            return Response(final_response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    
class TeacherCourseProgressListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        db = get_mongo_db()

        # Check if user is a teacher
        if not hasattr(request.user, '_mongo_doc') or request.user._mongo_doc.get('role') != 'TEACHER':
            return Response(
                {"error": "Access denied. Only teachers can view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            course_oid = ObjectId(course_id)
        except Exception:
            return Response({"error": "Invalid course_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Find the course to get its name
        course = db.courses.find_one({"_id": course_oid})
        if not course:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        # Find all progress documents for this course (to get students)
        progress_records_cursor = db.course_progress.find({"course_id": course_oid})
        progress_records = list(progress_records_cursor)

        # Get total number of students
        total_students = len(progress_records)

        # Get all assignments for this course
        assignments = list(db.assignments.find({"course_id": course_oid}))
        assignments_data = []
        for assignment in assignments:
            assignments_data.append({
                "id": str(assignment['_id']),
                "title": assignment.get('title'),
                "description": assignment.get('description'),
                "due_date": assignment.get('due_date').isoformat() if assignment.get('due_date') else None,
                "created_at": assignment.get('created_at').isoformat() if assignment.get('created_at') else None,
                "status": assignment.get('status')
            })

        # Get upcoming live classes (scheduled after now)
        now = datetime.datetime.now()
        upcoming_classes = list(db.live_classes.find({
            "course_id": course_oid,
            "scheduled_time": {"$gt": now}
        }).sort("scheduled_time", 1))  # Sort by scheduled_time ascending

        upcoming_classes_data = []
        for class_ in upcoming_classes:
            upcoming_classes_data.append({
                "id": str(class_['_id']),
                "title": class_.get('title'),
                "description": class_.get('description'),
                "scheduled_time": class_.get('scheduled_time').isoformat() if class_.get('scheduled_time') else None,
                "duration_minutes": class_.get('duration_minutes'),
                "meeting_url": class_.get('meeting_url')
            })

        # Prepare student progress data
        response_data = []
        for record in progress_records:
            # Fetch user details for each progress record
            user_doc = db.customusers.find_one({"_id": record['user_id']})  # user_id is ObjectId here

            user_info = {
                "id": str(user_doc['_id']),
                "email": user_doc.get('email'),
                "first_name": user_doc.get('first_name'),
                "last_name": user_doc.get('last_name'),
                "username": user_doc.get('username')
            } if user_doc else {"id": str(record['user_id']), "email": "Unknown User", "first_name": "", "last_name": "", "username": ""}

            response_data.append({
                "student_info": user_info,
                "course_id": str(record['course_id']),
                "course_name": course.get('name'),  # Add course name here
                "progress_percentage": record.get('progress_percentage', 0),
                "details": record.get('details', {}),
                "last_updated": record.get('last_updated').isoformat() if record.get('last_updated') else None
            })

        # Construct final response with all data
        final_response = {
            "course_info": {
                "course_id": course_id,
                "course_name": course.get('name'),
                "total_students": total_students
            },
            "assignments": assignments_data,
            "upcoming_classes": upcoming_classes_data,
            "student_progress": response_data
        }

        return Response(final_response, status=status.HTTP_200_OK)
    
logger = logging.getLogger(__name__)

class GetCurrentUserProfile(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            db = get_mongo_db()
            user_id = str(request.user.id)
            
            # Fetch user document (trying both collections)
            user_data = db.customusers.find_one({"_id": ObjectId(user_id)}, {'password': 0})
            if not user_data:
                user_data = db.teacherprofiles.find_one({"_id": ObjectId(user_id)}, {'password': 0})
                if not user_data:
                    return Response(
                        {"error": "User not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Convert MongoDB document to JSON-serializable format
            serialized_data = json.loads(json.dumps(user_data, default=bson_default))
            
            return Response(serialized_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}", exc_info=True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

logger = logging.getLogger(__name__)

# Configure Brevo (same as you have it in signals.py)
configuration = brevo_sdk.Configuration()
configuration.api_key['api-key'] = settings.BREVO_API_KEY
api_instance = brevo_sdk.TransactionalEmailsApi(brevo_sdk.ApiClient(configuration))

# --- New Serializer for input validation ---
class SendTemplate1Serializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    


# --- New API View ---
class SendTemplate1View(APIView):


    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = SendTemplate1Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_email = serializer.validated_data['email']
        
        # webinar_link = serializer.validated_data['webinar_link'] # DELETE OR COMMENT THIS LINE

        BREVO_TEMPLATE_1_ID = 1 # <--- Your actual template ID

        template_params = {
            "PDF_DOWNLOAD_LINK": 'https://titanscareers.s3.eu-north-1.amazonaws.com/media/Launch-Your-UK-Career-Titans-Careers-Guide.pdf'
            # "WEBINAR_LINK": webinar_link, # DELETE OR COMMENT THIS LINE
        }

        send_smtp_email = brevo_sdk.SendSmtpEmail(
            to=[{"email": recipient_email}],
            template_id=BREVO_TEMPLATE_1_ID,
            params=template_params, # Pass parameters here
            # Optional: Set a sender if different from default configured in Brevo
            # sender={"name": "Your App Name", "email": "no-reply@yourdomain.com"},
            # Optional: Subject can be overridden, but templates usually handle this
            # subject="Subject for Template 1",
        )

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Brevo Template 1 sent successfully to {recipient_email}. Response: {api_response}")
            return Response(
                {"message": f"Brevo Template 1 sent successfully to {recipient_email}."},
                status=status.HTTP_200_OK
            )
        except ApiException as e:
            logger.error(f"Brevo API Error sending Template 1 to {recipient_email}: {e}")
            return Response(
                {"error": "Failed to send email via Brevo.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error sending Template 1 to {recipient_email}: {e}")
            return Response(
                {"error": "An unexpected error occurred while sending the email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )