from rest_framework import serializers
from rest_framework.validators import ValidationError
from .models import *
import re
from django.contrib.auth.hashers import make_password

# This will check length and type of characters passed in password
def check_password(password):
    password_pattern = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    match = re.match(password_pattern, string=password)
    return bool(match)

def validate_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if check_password(password) == False:
        raise ValidationError("Password must contain at least one uppercase, one lowercase, one digit and one special character")

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number', 'created_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'created_at': {'read_only': True},
            'phone_number': {'required': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        hashed_password = make_password(password)  # Hash the password here

        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            password=hashed_password  # Save the hashed password
        )
        return user


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'role', 'bio', 'profile_picture', 'phone_number', 'past_experience', 'course_taken', 'created_at'
        ]
        extra_kwargs = {
            'user': {'required': True},
            'created_at': {'read_only': True},
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = CustomUser.objects.create(**user_data)
        teacher_profile = TeacherProfile.objects.create(user=user, **validated_data)
        return teacher_profile