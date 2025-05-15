# views.py

from django.shortcuts import render
from rest_framework import status
from .serializer import CustomUserSerializer, TeacherProfileSerializer, NotificationSerializer
from courses.serializer import CourseSerializer, CourseProgressResponseSerializer

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

db = get_mongo_db()
users_collection = db['users']

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

            # Extract user info from the token
            user_info = {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo['name'],
                'picture': idinfo.get('picture', ''),
                'last_login': datetime.utcnow(),
            }

            # Check if the user already exists in the database
            user = users_collection.find_one({'google_id': idinfo['sub']})
            if not user:
                logger.info(f"Creating new user: {user_info['email']}")
                # Create a new user if not exists
                users_collection.insert_one(user_info)
                user = user_info
            else:
                logger.info(f"User already exists: {user_info['email']}")

            # Create a session for the user
            request.session['user_id'] = str(user['_id'])
            request.session.modified = True

            logger.info(f"Successfully logged in user: {user_info['email']}")
            return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Error verifying Google token: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return Response({'error': 'An unexpected error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Signup(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = serializer.data  # Ensure ObjectId is converted to string
            return Response({"user": user_data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        db = get_mongo_db()
        user = db.customusers.find_one({"email": email})

        if user and check_password(password, user['password']):
            serializer = CustomUserSerializer(user)
            user_data = serializer.data
            # user_data['id'] = int(user_data['id'])  # Ensure ObjectId is converted to string
            return Response({"user": user_data, "message": "User logged in successfully"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid credentials, please try again"}, status=status.HTTP_400_BAD_REQUEST)

class Logout(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)

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
        teachers = db.teacher_profiles.find()
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