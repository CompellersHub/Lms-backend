from django.shortcuts import render
from rest_framework import status
from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# Create your views here.
class Courses(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
    
class CourseDetail(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        course = Course.objects.get(id=pk)
        serializer = CourseSerializer(course)
        return Response(serializer.data)
    
    
    def put(self, request, pk):
        course = Course.objects.get(id=pk)
        serializer = CourseSerializer(instance=course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        course = Course.objects.get(id=pk)
        course.delete()
        return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
class Categories(APIView):
    
    def get(self, request):
        categories = Category.objects.all()
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
        try:
            category = Category.objects.get(id=pk)
            course = Course.objects.filter(category=category)
            serializer = CourseSerializer(course, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

