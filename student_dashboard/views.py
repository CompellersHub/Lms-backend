from django.shortcuts import render
from rest_framework import status
from .models import StudentProfile
from rest_framework.views import APIView
from rest_framework.response import Response
from courses.models import Course
from courses.serializer import CourseSerializer
from .serializer import StudentSerializer
from rest_framework.permissions import IsAuthenticated

# Create your views here.

class Profile(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        student = request.user
        enrolled_courses = Course.objects.filter(student=student)

        student_serializer = StudentSerializer(student) 
        enrolled_courses_serializer = CourseSerializer(enrolled_courses, many=True)

        data = {
            'student': student_serializer.data,
            'enrolled_courses': enrolled_courses_serializer.data,
        }
        return Response(data)