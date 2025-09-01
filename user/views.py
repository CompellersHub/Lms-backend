# views.py

from django.shortcuts import render
from rest_framework import status

from blog.models import BlogUser
from blog.serializer import BlogUserSerializer
from user.services import EmailService
from user.utils.email_service import send_brevo_email
from .serializer import CourseProgressSerializer, CustomUserSerializer, IndividualEmailSerializer, MassEmailSerializer, TeacherProfileSerializer, NotificationSerializer, CourseProgressRecordSerializer, CourseProgressResponseSerializer
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
from datetime import datetime
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
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import OTP
from .tasks import send_application_received_email, send_teacher_approval_email, send_teacher_rejection_email, send_welcome_otp


db = get_mongo_db()
users_collection = db['customusers']

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

            # Convert timezone-aware datetime to naive datetime for MongoDB storage
            current_time = timezone.now()  # Using Django's timezone utility

            
            extracted_user_info = {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'name': idinfo.get('name', ''),
                'profile_picture': idinfo.get('picture', ''),
                'last_login': current_time,
                'role': 'STUDENT',
                'username': idinfo.get('email', '').split('@')[0],
                'phone_number': '',
                'course': [],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'date_joined': current_time,
            }

            db = get_mongo_db()
            users_collection = db['customusers']

            # Check for existing user by Google ID first
            user_document = users_collection.find_one({'google_id': idinfo['sub']})
            
            if not user_document:
                # Check for existing user by email if no Google user found
                user_document = users_collection.find_one({'email': extracted_user_info['email']})
                
                if user_document:
                    logger.info(f"Linking Google credentials to existing user: {extracted_user_info['email']}")
                    # Update existing user with Google credentials
                    update_data = {
                        'google_id': idinfo['sub'],
                        'last_login': current_time,
                    }
                    # Only update name fields if they're not already set
                    if not user_document.get('first_name'):
                        update_data['first_name'] = extracted_user_info['first_name']
                    if not user_document.get('last_name'):
                        update_data['last_name'] = extracted_user_info['last_name']
                    if not user_document.get('profile_picture'):
                        update_data['profile_picture'] = extracted_user_info['profile_picture']

                    users_collection.update_one(
                        {'email': extracted_user_info['email']},
                        {'$set': update_data}
                    )
                    user_document = users_collection.find_one({'email': extracted_user_info['email']})
                else:
                    # Create new user
                    logger.info(f"Creating new user with Google credentials: {extracted_user_info['email']}")
                    inserted_result = users_collection.insert_one(extracted_user_info)
                    user_document = users_collection.find_one({'_id': inserted_result.inserted_id})

            # Create Django user instance for JWT token generation
            try:
                user = CustomUser.from_mongo(user_document)
                tokens = create_jwt_tokens(user)
                
            except Exception as e:
                logger.error(f"Failed to generate JWT tokens: {str(e)}", exc_info=True)
                return Response(
                    {'error': 'Authentication failed - could not generate tokens'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = CustomUserSerializer(user_document)

            logger.info(f"Successful Google login for user: {user_document['email']}")
            return Response({
                'message': 'Login successful',
                'user': serializer.data,
                'access': tokens['access'],
                'refresh': tokens['refresh'],
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Error verifying Google token: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in Google login: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An unexpected error occurred during authentication'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)
    

class TeacherSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Required fields with validation
        required_fields = {
            'email': str,
            'first_name': str,
            'last_name': str,
            'bio': str,
            'password': str,
            'course_taken': str,
        }

        # Optional fields with defaults
        optional_fields = {
            'profile_picture': 'https://titanscareers.s3.amazonaws.com/Teacher_profile/placeholder.png',
            'phone_number': '',
            'past_experience': '',
            'django_id': None,
            'username': ''
        }

        data = request.data.copy()
        
        # Validate required fields
        missing_fields = []
        for field, field_type in required_fields.items():
            if field not in data:
                missing_fields.append(field)
            elif not isinstance(data[field], field_type):
                try:
                    data[field] = field_type(data[field])
                except (ValueError, TypeError):
                    return Response(
                        {"error": f"Invalid format for {field}. Expected {field_type.__name__}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set default values for optional fields
        for field, default_value in optional_fields.items():
            if field not in data:
                data[field] = default_value

        # Email validation
        if not data['email'].endswith('@gmail.com'):
            return Response(
                {"error": "Only Gmail addresses are currently supported"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        db = get_mongo_db()
        if db.teacherprofiles.find_one({"email": data['email']}):
            return Response(
                {"error": "Teacher with this email already exists"},
                status=status.HTTP_409_CONFLICT
            )

        # Prepare the teacher document
        teacher_data = {
            '_id': ObjectId(),
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'role': 'TEACHER',
            'bio': data['bio'],
            'profile_picture': data['profile_picture'],
            'phone_number': data['phone_number'],
            'past_experience': data['past_experience'],
            'course_taken': data['course_taken'],
            'created_at': timezone.now(),
            'email': data['email'],
            'password': make_password(data['password']),
            'username': data['username'],
            'last_login': None,
            'is_verified': False,
            'verification_status': 'pending',  # New field
            'application_date': timezone.now()  # New field
        }

        try:
            # Store unverified teacher
            db.teacherprofiles.insert_one(teacher_data)
            logger.info(f"Teacher created: {teacher_data['email']}")

            # Send application received email
            try:
                task = send_application_received_email.delay(
                    to_email=data['email'],
                    first_name=data['first_name']
                )
                logger.info(f"Celery task created with ID: {task.id}")
            except Exception as e:
                logger.error(f"Failed to queue email task: {str(e)}")
                # Immediate fallback
                try:
                    send_brevo_email(
                        to_email=data['email'],
                        template_id=7,
                        params={'FIRST_NAME': data['first_name']}
                    )
                except Exception as email_error:
                    logger.error(f"Failed to send email directly: {str(email_error)}")
    
            return Response({
                "message": "Application submitted for review",
                "teacher_id": str(teacher_data['_id']),
                "email": data['email']
            }, status=201)

        except Exception as e:
            logger.error(f"Signup failed: {str(e)}")
            return Response(
                {"error": "Registration failed. Please try again."},
                status=500
            )





class AdminTeacherVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get list of unverified teachers for admin review
        """
        db = get_mongo_db()
        unverified_teachers = list(db.teacherprofiles.find({"is_verified": False}))
        
        # Serialize the data
        teachers_data = []
        for teacher in unverified_teachers:
            teachers_data.append({
                "teacher_id": str(teacher['_id']),
                "first_name": teacher['first_name'],
                "last_name": teacher['last_name'],
                "email": teacher['email'],
                "bio": teacher['bio'],
                "course_taken": teacher['course_taken'],
                "past_experience": teacher['past_experience'],
                "created_at": teacher['created_at'],
                "profile_picture": teacher['profile_picture']
            })
        
        return Response({"unverified_teachers": teachers_data}, status=status.HTTP_200_OK)

class AdminTeacherVerificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, teacher_id):
        """
        Approve or reject a specific teacher application
        """
        action = request.data.get('action')  # 'approve' or 'reject'
        feedback = request.data.get('feedback', '')

        if not action or action not in ['approve', 'reject']:
            return Response(
                {"error": "Invalid action. Must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            teacher_oid = ObjectId(teacher_id)
        except:
            return Response(
                {"error": "Invalid teacher ID format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        db = get_mongo_db()
        teacher = db.teacherprofiles.find_one({"_id": teacher_oid})

        if not teacher:
            return Response(
                {"error": "Teacher not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if teacher.get('verification_status') != 'pending':
            return Response(
                {"error": "This application has already been processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action == 'approve':
            # Update teacher as verified
            db.teacherprofiles.update_one(
                {"_id": teacher_oid},
                {
                    "$set": {
                        "is_verified": True,
                        "verification_status": "approved",
                        "verified_at": timezone.now(),
                        "verification_feedback": None
                    }
                }
            )

            # Send approval email
            try:
                send_teacher_approval_email.delay(
                    to_email=teacher['email'],
                    first_name=teacher['first_name']
                )
            except Exception as e:
                logger.error(f"Failed to queue approval email: {str(e)}")
                send_teacher_approval_email(
                    to_email=teacher['email'],
                    first_name=teacher['first_name']
                )

            return Response(
                {"message": "Teacher approved and notification sent"},
                status=status.HTTP_200_OK
            )
        
        else:  # reject
            # Update teacher with feedback
            db.teacherprofiles.update_one(
                {"_id": teacher_oid},
                {
                    "$set": {
                        "verification_status": "rejected",
                        "verification_feedback": feedback,
                        "rejected_at": timezone.now()
                    }
                }
            )

            # Send rejection email
            try:
                send_teacher_rejection_email.delay(
                    to_email=teacher['email'],
                    first_name=teacher['first_name'],
                    feedback=feedback
                )
            except Exception as e:
                logger.error(f"Failed to queue rejection email: {str(e)}")
                send_teacher_rejection_email(
                    to_email=teacher['email'],
                    first_name=teacher['first_name'],
                    feedback=feedback
                )

            return Response(
                {"message": "Teacher rejected and notification sent"},
                status=status.HTTP_200_OK
            )
        


class TeacherLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Extract credentials from request
        email = request.data.get("email")
        password = request.data.get("password")

        # Validate required fields
        if not email or not password:
            return Response(
                {"error": "Both email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 1: Check teacher exists in MongoDB
        db = get_mongo_db()
        teacher = db.teacherprofiles.find_one({"email": email})
        
        if not teacher:
            return Response(
                {"error": "Teacher account not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Step 2: Verify password
        if not check_password(password, teacher['password']):
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        

        # Check if teacher is verified
        if not teacher.get('is_verified', False):
            return Response(
                {
                    "error": "Your account is pending verification",
                    "detail": "Please wait for admin approval before logging in"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Step 3: Authenticate user
        user = authenticate(request=request, email=email, password=password)
        if not user or not hasattr(user, 'role') or user.role != 'TEACHER':
            return Response(
                {"error": "Authentication failed or invalid user role"},
                status=status.HTTP_403_FORBIDDEN
            )

        # if not user.is_active:
        #     return Response(
        #         {"error": "Teacher account is inactive"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        # Step 4: Update last login and prepare response
        db.teacherprofiles.update_one(
            {"_id": user._mongo_doc['_id']},
            {"$set": {"last_login": timezone.now()}}
        )

        updated_teacher = db.teacherprofiles.find_one({"_id": user._mongo_doc['_id']})
        serializer = TeacherProfileSerializer(updated_teacher)
        tokens = create_jwt_tokens(user)

        return Response({
            "access": tokens['access'],
            "refresh": tokens['refresh'],
            "teacher": serializer.data,
            "message": "Login successful"
        }, status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        data = request.data.copy()
        
        # Define restricted fields that shouldn't be updated via this endpoint
        base_restricted_fields = ['role', 'created_at', 'last_login', 'password']
        
        # Role-specific restricted fields
        role_restricted_fields = {
            'TEACHER': ['course_taken', '_id', 'user_id', 'email'],
            'STUDENT': ['courses_enrolled', '_id', 'username', 'email']
        }
        
        # Get all restricted fields for the user's role
        restricted_fields = base_restricted_fields + role_restricted_fields.get(user.role, [])

        # Remove all restricted fields from update data
        for field in restricted_fields:
            data.pop(field, None)

        db = get_mongo_db()
        
        try:
            # Determine user type and collection
            if hasattr(user, 'role'):
                if user.role == 'TEACHER':
                    collection = 'teacherprofiles'
                    serializer_class = TeacherProfileSerializer
                elif user.role == 'STUDENT':
                    collection = 'customusers'
                    serializer_class = CustomUserSerializer
                else:
                    return Response(
                        {"error": "Unsupported user role for update"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {"error": "User role not defined"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the current document
            current_doc = db[collection].find_one({"_id": ObjectId(str(user.id))})
            if not current_doc:
                return Response(
                    {"error": "User profile not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate fields against serializer and remove any invalid fields
            serializer_fields = serializer_class().get_fields()
            update_data = {
                field: data[field] 
                for field in data 
                if field in serializer_fields and field not in restricted_fields
            }

            if not update_data:
                return Response(
                    {"error": "No valid fields provided for update"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Add updated_at timestamp
            update_data['updated_at'] = timezone.now()

            # Perform the update
            result = db[collection].update_one(
                {"_id": ObjectId(str(user.id))},
                {"$set": update_data}
            )

            if result.modified_count == 0:
                return Response(
                    {"error": "No changes were made"},
                    status=status.HTTP_304_NOT_MODIFIED
                )

            # Fetch the updated document
            updated_doc = db[collection].find_one({"_id": ObjectId(str(user.id))})
            serializer = serializer_class(updated_doc)

            return Response({
                "message": "Profile updated successfully",
                "user_info": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        
        if not email or not otp_code:
            return Response(
                {"error": "Email and OTP code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            otp = OTP.objects.filter(email=email, is_verified=False).latest('created_at')
        except OTP.DoesNotExist:
            return Response(
                {"error": "No pending OTP verification found for this email"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if otp.is_expired():
            return Response(
                {"error": "OTP has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp.verify(otp_code):
            # Move from temporary storage to actual collection
            db = get_mongo_db()
            temp_user = db.unverified_teachers.find_one({"email": email})
            
            if not temp_user:
                return Response(
                    {"error": "User data not found. Please register again."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create the actual teacher profile
            temp_user['is_verified'] = True
            temp_user['created_at'] = timezone.now()
            result = db.teacherprofiles.insert_one(temp_user)
            
            # Clean up
            db.unverified_teachers.delete_one({"_id": temp_user['_id']})
            
            return Response({
                "message": "Account verified successfully",
                "user_id": str(result.inserted_id)
            }, status=status.HTTP_200_OK)
        
        return Response(
            {"error": "Invalid OTP code"},
            status=status.HTTP_400_BAD_REQUEST
        )

    
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

class TeacherDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        db = get_mongo_db()

        # Check if user is a teacher
        if not hasattr(request.user, '_mongo_doc') or request.user._mongo_doc.get('role') != 'TEACHER':
            return Response(
                {"error": "Access denied. Only teachers can view this resource."},
                status=status.HTTP_403_FORBIDDEN
            )

        teacher_id = request.user._mongo_doc['_id']

        # 1. Get total number of courses taught by this teacher
        total_courses = db.courses.count_documents({"teacher_id": teacher_id})

        # 2. Get all courses taught by this teacher
        teacher_courses = list(db.courses.find({"teacher_id": teacher_id}))
        course_ids = [course['_id'] for course in teacher_courses]

        # Get total students across all courses
        total_students = db.course_progress.count_documents({"course_id": {"$in": course_ids}})

        # 3. Get pending assignments (submissions not made)
        pending_assignments_count = 0
        assignments = list(db.assignments.find({"course_id": {"$in": course_ids}}))
        
        for assignment in assignments:
            # Count students who haven't submitted this assignment
            total_students_in_course = db.course_progress.count_documents({
                "course_id": assignment['course_id']
            })
            
            submitted_count = db.assignment_submissions.count_documents({
                "assignment_id": assignment['_id'],
                "status": "submitted"
            })
            
            pending_assignments_count += (total_students_in_course - submitted_count)

        # 4. Get upcoming live classes (within next 30 days)
        now = datetime.datetime.now()
        thirty_days_later = now + datetime.timedelta(days=30)
        
        upcoming_classes = list(db.live_classes.find({
            "course_id": {"$in": course_ids},
            "scheduled_time": {
                "$gt": now,
                "$lt": thirty_days_later
            }
        }).sort("scheduled_time", 1).limit(5))  # Get next 5 upcoming classes

        upcoming_classes_data = []
        for class_ in upcoming_classes:
            # Get course name for each class
            course = db.courses.find_one({"_id": class_['course_id']})
            upcoming_classes_data.append({
                "id": str(class_['_id']),
                "title": class_.get('title'),
                "course_name": course.get('name') if course else "Unknown Course",
                "scheduled_time": class_.get('scheduled_time').isoformat() if class_.get('scheduled_time') else None,
                "duration_minutes": class_.get('duration_minutes')
            })

        response_data = {
            "total_courses": total_courses,
            "total_students": total_students,
            "pending_assignments": pending_assignments_count,
            "upcoming_classes": upcoming_classes_data,
            "upcoming_classes_count": len(upcoming_classes_data)
        }

        return Response(response_data, status=status.HTTP_200_OK)


class TeacherEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle both individual and mass email based on request data"""
        # Check if it's individual or mass email
        if 'student_email' in request.data:
            serializer = IndividualEmailSerializer(data=request.data)
        elif 'student_emails' in request.data:
            serializer = MassEmailSerializer(data=request.data)
        else:
            return Response(
                {"error": "Must provide either student_email or student_emails"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            email_service = EmailService()
            data = serializer.validated_data
            
            # Prepare HTML content - FIXED: No backslashes in f-string expressions
            message_html = data['message'].replace('\n', '<br>')
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{data['subject']}</title>
</head>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">{data['subject']}</h2>
        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
            {message_html}
        </div>
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            Sent by: {data['teacher_name']} ({data['teacher_email']})
        </p>
    </div>
</body>
</html>
            """
            
            if 'student_email' in data:
                # Individual email
                success = email_service.send_individual_email(
                    to_email=data['student_email'],
                    subject=data['subject'],
                    html_content=html_content,
                    teacher_name=data['teacher_name'],
                    teacher_email=data['teacher_email']
                )
                
                if success:
                    # Log the email sending
                    self._log_email(
                        request.user,
                        [data['student_email']],
                        data['subject'],
                        "individual"
                    )
                    
                    return Response({
                        "success": True,
                        "message": "Email sent successfully",
                        "recipient": data['student_email'],
                        "type": "individual"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Failed to send email"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            else:
                # Mass email
                success_count = email_service.send_mass_email(
                    to_emails=data['student_emails'],
                    subject=data['subject'],
                    html_content=html_content,
                    teacher_name=data['teacher_name'],
                    teacher_email=data['teacher_email']
                )
                
                if success_count > 0:
                    # Log the email sending
                    self._log_email(
                        request.user,
                        data['student_emails'],
                        data['subject'],
                        "mass"
                    )
                    
                    return Response({
                        "success": True,
                        "message": f"Emails sent to {success_count} recipients",
                        "total_recipients": len(data['student_emails']),
                        "successful_sends": success_count,
                        "type": "mass"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Failed to send any emails"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Email sending process failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _log_email(self, user, recipients, subject, email_type):
        """Log email activity to database"""
        # You can implement logging to your database here
        logger.info(f"Teacher {user.email} sent {email_type} email to {len(recipients)} recipients: {subject}")