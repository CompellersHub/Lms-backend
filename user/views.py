from django.shortcuts import render
from rest_framework import status
from .models import CustomUser
from .serializer import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import Token
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model


# User = get_user_model()

# Create your views here.
class Signup(APIView):
    def post(self, request, format=None):
        serializers = UserSerializer(data=request.data)
        if serializers.is_valid():
            user = serializers.save()
            print(f"User created: {user}, ID: {user.id}")
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({"token": token.key, "user": serializers.data}, status=status.HTTP_201_CREATED)
        return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)
class Login(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
class Logout(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def post(self, request):
        request.user.auth_token.delete()
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