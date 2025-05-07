# views.py

from django.shortcuts import render
from rest_framework import status
from .serializer import CustomUserSerializer, TeacherProfileSerializer, NotificationSerializer
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
                # Create a new user if not exists
                users_collection.insert_one(user_info)
                user = user_info

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
        user = db.users.find_one({"email": email})

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
        students = db.users.find()
        serializer = CustomUserSerializer([student for student in students], many=True)
        return Response(serializer.data)
    
class StudentDetail(APIView):
    def get(self, request, student_id):
        db = get_mongo_db()
        student = db.users.find_one({"_id": ObjectId(student_id)})
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomUserSerializer(student)
        return Response(serializer.data)

    def put(self, request, student_id):
        db = get_mongo_db()
        student = db.users.find_one({"_id": ObjectId(student_id)})
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

class StudentNotificationsView(APIView):
    def get(self, request, student_id):
        student = db.users.find_one({"_id": ObjectId(student_id)})
        if not student:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        notifications = db.notifications.find({"student_id": ObjectId(student_id)})
        serializer = NotificationSerializer([notification for notification in notifications], many=True)
        return Response(serializer.data)
    
def social_callback(request):
    return HttpResponseRedirect("http://127.0.0.1:5503/course.html")
