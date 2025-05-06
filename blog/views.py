from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import CategorySerializer, BlogSerializer, BlogUserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.hashers import check_password
from django.contrib.auth import logout
from courses.mongo_utils import get_mongo_db
from bson.objectid import ObjectId
from bson.errors import InvalidId

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

        db = get_mongo_db()
        user = db.blogusers.find_one({"email": email})

        if user and check_password(password, user['password']):
            serializer = BlogUserSerializer(user)
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
