import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, login
from user.utils.token_utils import create_jwt_tokens
from .serializer import CategorySerializer, BlogSerializer, BlogUserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.hashers import check_password
from django.contrib.auth import logout
from courses.mongo_utils import get_mongo_db
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timedelta

# Initialize the MongoDB database connection
db = get_mongo_db()

class CategoryListCreateView(APIView):
    def get(self, request):
        categories = db.categories.find()
        serializer = CategorySerializer(list(categories), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailView(APIView):
    def get(self, request, pk):
        try:
            category = db.categories.find_one({"_id": ObjectId(pk)})
            if not category:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = CategorySerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            category = db.categories.find_one({"_id": ObjectId(pk)})
            if not category:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = CategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                updated_category = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            result = db.categories.delete_one({"_id": ObjectId(pk)})
            if result.deleted_count == 0:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

class BlogListCreateView(APIView):
    def get(self, request):
        blogs = db.blogs.find()
        serializer = BlogSerializer(list(blogs), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = BlogSerializer(data=request.data)
        if serializer.is_valid():
            blog = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BlogDetailView(APIView):
    def get(self, request, pk):
        try:
            blog = db.blogs.find_one({"_id": ObjectId(pk)})
            if not blog:
                return Response({"detail": "Blog not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = BlogSerializer(blog)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            blog = db.blogs.find_one({"_id": ObjectId(pk)})
            if not blog:
                return Response({"detail": "Blog not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = BlogSerializer(blog, data=request.data, partial=True)
            if serializer.is_valid():
                updated_blog = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            result = db.blogs.delete_one({"_id": ObjectId(pk)})
            if result.deleted_count == 0:
                return Response({"detail": "Blog not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except InvalidId:
            return Response({"detail": "Invalid ID format."}, status=status.HTTP_400_BAD_REQUEST)

class Signup(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = BlogUserSerializer(data=request.data)
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

        user = authenticate(request=request, email=email, password=password)

        if user is not None:
            if user.is_active:
                # IMPORTANT: Role check for students
                # Ensure this login endpoint is specifically for students
                # Or, if it's a general login, ensure the user has the 'STUDENT' role.
                # Assuming 'customusers' collection is for students/general users with a role field.
                db = get_mongo_db()
                custom_user_doc = db.bloguser.find_one({"_id": user._mongo_doc['_id']}) # Get the full doc again if needed

                if not custom_user_doc or custom_user_doc.get('role') != "blogger":
                    return Response(
                        {"detail": _('Only students can log in via this endpoint or incorrect role.')},
                        status=status.HTTP_403_FORBIDDEN # Or 401 if you prefer
                    )

                # Generate JWT tokens manually
                tokens = create_jwt_tokens(user)

                # Update last_login in MongoDB (if not handled by backend)
                # Your backend might already update this, but doing it here ensures it.
                db.bloguser.update_one(
                    {"_id": user._mongo_doc['_id']},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                
                # Re-fetch the updated document for the response, including updated last_login
                updated_user_document = db.bloguser.find_one({"_id": user._mongo_doc['_id']})

                # Use CustomUserSerializer to serialize the full MongoDB document for the response.
                serializer = BlogUserSerializer(updated_user_document)

                return Response({
                    "access": tokens['access'],
                    "refresh": tokens['refresh'],
                    "user_info": serializer.data, # Renamed 'user' to 'user_info' for consistency with TeacherLoginView
                    "message": "Student logged in successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "User account is inactive."}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            # Authentication failed (either user not found or password incorrect)
            return Response({"error": "Invalid credentials, please try again"}, status=status.HTTP_400_BAD_REQUEST)

class Logout(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)
