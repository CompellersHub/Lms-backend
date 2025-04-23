from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from bson.objectid import ObjectId
from datetime import datetime
from .serializer import (
    CategorySerializer,
    BlogSerializer
)
from courses.mongo_utils import get_mongo_db

# Create your views here.
class Category(APIView):
    def get(self, request):
        db = get_mongo_db()
        category = list(db.categories.find())
        serializer = CategorySerializer(category, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class Blog(APIView):
    def get(self, request):
        db = get_mongo_db()
        blog = list(db.blogs.find())
        serializer = BlogSerializer(blog, many=True)
        return Response(serializer.data)