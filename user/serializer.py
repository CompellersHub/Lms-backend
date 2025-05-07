# serializers.py

from rest_framework import serializers
from rest_framework.validators import ValidationError
from courses.mongo_utils import get_mongo_db
from bson import ObjectId
from django.contrib.auth.hashers import make_password
import re
import datetime


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
    course = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True) # Expecting a list of embedded Course dictionaries
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    role = serializers.CharField(max_length=20, default='STUDENT')
    phone_number = serializers.CharField(max_length=15, allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)


    def validate_username(self, value):
        db = get_mongo_db()
        if db.customusers.find_one({"username": value}):
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        db = get_mongo_db()
        if db.customusers.find_one({"email": value}):
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        representation['course'] = [] # Initialize as an empty list

        courses_data = instance.get('course', [])
        if courses_data:
            from courses.serializer import CourseSerializer
            for course_data in courses_data:
                try:
                    representation['course'].append(CourseSerializer().to_representation(course_data))
                except Exception as e:
                    print(f"Error serializing embedded course data: {e}")

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['created_at'] = datetime.utcnow()
        result = db.customusers.insert_one(validated_data)
        return db.customusers.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        user_id = ObjectId(instance['id'])
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        db.users.update_one({"_id": user_id}, {"$set": validated_data})
        return db.customusers.find_one({"_id": user_id})

class TeacherProfileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField()
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
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

class NotificationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    student = CustomUserSerializer()
    message = serializers.CharField()
    is_read = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'student' in instance and isinstance(instance['student'], dict):
            instance['student'] = CustomUserSerializer().to_representation(instance['student'])
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.notifications.insert_one(validated_data)
        return db.notifications.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        notification_id = ObjectId(instance['id'])
        db.notifications.update_one({"_id": notification_id}, {"$set": validated_data})
        return db.notifications.find_one({"_id": notification_id})