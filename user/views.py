from django.shortcuts import render
from rest_framework import status
from .models import CustomUser, TeacherProfile
from .serializer import CustomUserSerializer, TeacherProfileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
# from rest_framework_simplejwt.tokens import Token
# from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseRedirect
# Create your views here.

class Signup(APIView):
    permission_classes = [AllowAny]
    def post(self, request, format=None):
        serializers = CustomUserSerializer(data=request.data)
        if serializers.is_valid():
            user = serializers.save()
            print(f"User created: {user}, ID: {user.id}")
            # token, created = Token.objects.get_or_create(user=user)
            
            return Response({"user": serializers.data}, status=status.HTTP_201_CREATED)
        return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)
    
class Login(APIView):
    permission_classes = []
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        
        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response({"error": "Invalid credentials, please try again"}, status=status.HTTP_400_BAD_REQUEST)

        
        login(request, user)
        serializer = CustomUserSerializer(user)
        user_data = serializer.data
        # token, created = Token.objects.get_or_create(user=user)

        return Response({ "user": user_data, "message": "User logged in successfully"}, status=status.HTTP_200_OK)

class Logout(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        Logout(request)

        return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK) 
    

    



class Get_csrf_token(APIView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        csrf_token = get_token(request)
        response = JsonResponse({'message': 'CSRF token set.'})
        response['X-CSRFToken'] = csrf_token
        return response
    

def social_callback(request):
    return HttpResponseRedirect("http://127.0.0.1:5503/course.html")