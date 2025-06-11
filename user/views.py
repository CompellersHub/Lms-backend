# views.py

from django.shortcuts import render
from rest_framework import status
from .serializer import CustomUserSerializer, TeacherProfileSerializer, NotificationSerializer
from courses.serializer import CourseSerializer, CourseProgressResponseSerializer
from rest_framework_simplejwt.views import TokenObtainPairView # Use this for base JWT view
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
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

class Login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the user from MongoDB
        db = get_mongo_db()
        users_collection = db.customusers
        user_document = users_collection.find_one({"email": email})

        if user_document:
            # Check if the provided password matches the hashed password from MongoDB
            if 'password' in user_document and check_password(password, user_document['password']):
                # Update last_login in MongoDB
                users_collection.update_one(
                    {"_id": user_document['_id']},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                # Fetch the updated document to ensure 'last_login' is current in the response
                # This is important if you want the response to reflect the just-updated last_login
                user_document = users_collection.find_one({"_id": user_document['_id']})


                # Create a Django User object from MongoDB data
                # We need this to ensure the session and Django's auth system work correctly.
                # Populate it with necessary fields from the MongoDB document.
                user = CustomUser(
                    id=str(user_document['_id']), # Store MongoDB _id as Django user's PK
                    username=user_document.get('username', user_document['email']), # Use email as username if no dedicated username field
                    email=user_document['email'],
                    first_name=user_document.get('first_name', ''),
                    last_name=user_document.get('last_name', ''),
                    # Add other fields as needed from user_document to the Django CustomUser instance
                    # For example:
                    # phone_number=user_document.get('phone_number', ''),
                    # profile_picture=user_document.get('profile_picture', ''),
                    # role=user_document.get('role', 'STUDENT'),
                    is_active=user_document.get('is_active', True), # Get from mongo or default to True
                    is_staff=user_document.get('is_staff', False),
                    is_superuser=user_document.get('is_superuser', False),
                    date_joined=user_document.get('date_joined', timezone.now()),
                    last_login=user_document.get('last_login', None)
                )

                # --- CRUCIAL FIX: Retain user.backend ---
                # Important for sessions with custom authentication backends.
                # Make sure 'user.backends.MongoAuthBackend' matches your settings.AUTHENTICATION_BACKENDS entry.
                user.backend = 'user.backends.MongoAuthBackend'


                # Manually log in the user to create a session
                # If you are using Django's built-in session handling for authentication,
                # you might want to consider `auth.login(request, user)` here instead of manual session assignment.
                # However, your original code used `request.session['user_id']`, so I'll stick to that
                # while ensuring `user.backend` is set for proper session management.
                request.session['user_id'] = str(user_document['_id'])
                request.session.modified = True


                # Use CustomUserSerializer to serialize the full MongoDB document for the response.
                # Even though we created a Django `CustomUser` instance, for the *response data*,
                # we want the rich MongoDB document structure.
                serializer = CustomUserSerializer(user_document)


                # Include the session key in the response as requested
                return Response({
                    "user": serializer.data,
                    "message": "User logged in successfully",
                    "session_key": request.session.session_key # Retained as requested
                }, status=status.HTTP_200_OK)
            else:
                # Password does not match or password field missing
                return Response({"error": "Invalid credentials, please try again"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # User not found
            return Response({"error": "Invalid credentials, please try again"}, status=status.HTTP_400_BAD_REQUEST)



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

    # The 'course_id' parameter is now passed directly from the URL
    def get(self, request, course_id, format=None):
        query = {"role": "STUDENT"} # Always filter for students

        if not course_id:
            # This check is less likely to be hit with a path parameter
            # unless the URL pattern itself is malformed or optional,
            # but it's good for robustness.
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
            students_cursor = db.customusers.find(query)
            students_list = list(students_cursor)

            if not students_list:
                return Response(
                    {"message": f"No students found in course with ID '{course_id}'."},
                    status=status.HTTP_200_OK
                )

            serializer = CustomUserSerializer(students_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

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

        # Fetch counts of user activities for this course
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
        total_assignments = db.assignments.count_documents({"course._id": course_oid}) # Assuming assignments are linked by course ObjectId
        total_pdfs = db.course_library.count_documents({"course._id": course_oid, "file": {"$ne": None}, "url": {"$eq": None}}) # Assuming PDFs are stored as files in course_library

        if course.get('curriculum'):
            for module in course['curriculum']:
                if module.get('video'):
                    total_videos += len(module['video'])
                if module.get('course_note'):
                    total_notes += 1

        # Calculate overall progress (you might need to adjust weights)
        total_progress_points = completed_videos_count + opened_notes_count + assignments_submitted_count + pdfs_viewed_count
        total_possible_points = total_videos + total_notes + total_assignments + total_pdfs

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

        serializer = CourseProgressResponseSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            return Response({"error": "Invalid IDs"}, status=400)

        user = db.customusers.find_one({"_id": user_oid})
        course = db.courses.find_one({"_id": course_oid})

        if not user or not course:
            return Response({"error": "Not found"}, status=404)

        # Count user activities
        completed_videos = db.customuser_course_activity.count_documents({"user_id": user_oid, "course_id": course_oid, "activity_type": "video_completed"})
        opened_notes = db.customuser_course_activity.count_documents({"user_id": user_oid, "course_id": course_oid, "activity_type": "note_opened"})
        submitted_assignments = db.customuser_course_activity.count_documents({"user_id": user_oid, "course_id": course_oid, "activity_type": "assignment_submitted"})
        viewed_pdfs = db.customuser_course_activity.count_documents({"user_id": user_oid, "course_id": course_oid, "activity_type": "pdf_viewed"})

        # Count totals from the 'courses' collection
        total_videos = sum(len(module.get('video', [])) for module in course.get('curriculum', []))
        total_notes = sum(1 for module in course.get('curriculum', []) if module.get('course_note'))
        total_assignments = db.assignments.count_documents({"course_id": course_oid})
        total_pdfs = db.course_library.count_documents({"course_id": course_oid, "file": {"$ne": None}, "url": {"$eq": None}})

        # Calculate progress
        total_progress = completed_videos + opened_notes + submitted_assignments + viewed_pdfs
        total_possible = total_videos + total_notes + total_assignments + total_pdfs
        progress_percentage = int((total_progress / total_possible) * 100) if total_possible > 0 else 0

        response_data = {
            "user_id": str(user['_id']),
            "course_id": str(course['_id']),
            "course_name": course.get('name'),
            "progress_percentage": progress_percentage,
            "details": {
                "videos": {"completed": completed_videos, "total": total_videos},
                "course_notes": {"opened": opened_notes, "total": total_notes},
                "assignments": {"submitted": submitted_assignments, "total": total_assignments},
                "blog_pdfs": {"viewed": viewed_pdfs, "total": total_pdfs},
            }
        }
        return Response(response_data)