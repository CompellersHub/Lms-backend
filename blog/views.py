import datetime
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate, login
from courses.storages_backends import BlogMediaStorage
from user.utils.token_utils import create_jwt_tokens
from .serializer import BlogImageUploadSerializer, CategorySerializer, BlogSerializer, BlogUserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth.hashers import check_password
from django.contrib.auth import logout
from courses.mongo_utils import get_mongo_db
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timedelta
import hmac
import hashlib
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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

                if not custom_user_doc or custom_user_doc.get('role') != "Blogger":
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
    
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        logout(request)
        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)
    

class BlogImageUploadView(APIView):
    """
    Handles uploads for both:
    - Main blog images (type=main)
    - Content block images (type=content)
    """
    def post(self, request):
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_type = request.data.get('type', 'content')  # Default to content image
        image_file = request.FILES['image']
        
        # Validate image
        max_size = 5 * 1024 * 1024  # 5MB
        if image_file.size > max_size:
            return Response(
                {"error": f"Image size cannot exceed {max_size/1024/1024}MB"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_types = ['image/jpeg', 'image/png', 'image/webp']
        if image_file.content_type not in valid_types:
            return Response(
                {"error": "Only JPEG, PNG, and WebP images are allowed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Upload to S3 with different paths
        storage = BlogMediaStorage()
        ext = image_file.name.split('.')[-1].lower()
        
        if image_type == 'main':
            filename = f"main/{uuid.uuid4()}.{ext}"
        else:  # content
            filename = f"content/{uuid.uuid4()}.{ext}"
            
        saved_name = storage.save(filename, image_file)
        image_url = storage.url(saved_name)
        
        return Response({
            "success": True,
            "url": image_url,
            "type": image_type,
            "filename": filename
        }, status=status.HTTP_201_CREATED)
    




@csrf_exempt
def rankyak_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Verify signature
    signature = request.headers.get('X-RankYak-Signature')
    payload = request.body
    expected_signature = hmac.new(
        key=settings.RANKYAK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    # Process payload
    try:
        data = json.loads(payload.decode('utf-8'))
        event_type = data['event']
        
        if event_type == 'blog.published':
            blog_data = data['data']
            
            # Map RankYak data to your serializer format
            serialized_data = {
                'title': blog_data['title'],
                'slug': blog_data['slug'],
                'category': blog_data['category'],
                'tags': blog_data['tags'],
                'excerpt': blog_data['excerpt'],
                'content': blog_data['content'],
                'image_url': blog_data['featured_image'],
                'status': 'published' if settings.AUTO_PUBLISH else 'draft'
            }
            
            # Validate and save using your BlogSerializer
            serializer = BlogSerializer(data=serialized_data)
            if serializer.is_valid():
                blog = serializer.save()
                return JsonResponse({'status': 'success', 'blog_id': str(blog.id)})
            else:
                return JsonResponse({'error': serializer.errors}, status=400)
                
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'status': 'received'})
