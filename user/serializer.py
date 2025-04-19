# serializers.py

from rest_framework import serializers
from rest_framework.validators import ValidationError
from courses.mongo_utils import get_mongo_db
from bson import ObjectId
from django.contrib.auth.hashers import make_password
import re
from datetime import datetime

def check_password(password):
    password_pattern = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    match = re.match(password_pattern, string=password)
    return bool(match)

def validate_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not check_password(password):
        raise ValidationError("Password must contain at least one uppercase, one lowercase, one digit and one special character")

class CustomUserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    role = serializers.CharField(max_length=20, default='STUDENT')
    phone_number = serializers.CharField(max_length=15, allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_username(self, value):
        db = get_mongo_db()
        if db.users.find_one({"username": value}):
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        db = get_mongo_db()
        if db.users.find_one({"email": value}):
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['created_at'] = datetime.utcnow()
        result = db.users.insert_one(validated_data)
        return db.users.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        user_id = ObjectId(instance['id'])
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        db.users.update_one({"_id": user_id}, {"$set": validated_data})
        return db.users.find_one({"_id": user_id})

class TeacherProfileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField()
    role = serializers.CharField(max_length=20, default='TEACHER')
    bio = serializers.CharField(allow_blank=True, required=False)
    profile_picture = serializers.CharField(allow_blank=True, required=False)
    phone_number = serializers.CharField(max_length=15, allow_blank=True, required=False)
    past_experience = serializers.CharField(allow_blank=True, required=False)
    course_taken = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['created_at'] = datetime.utcnow()
        result = db.teacher_profiles.insert_one(validated_data)
        return db.teacher_profiles.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        profile_id = ObjectId(instance['id'])
        db.teacher_profiles.update_one({"_id": profile_id}, {"$set": validated_data})
        return db.teacher_profiles.find_one({"_id": profile_id})
