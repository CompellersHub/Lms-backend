# serializers.py

from rest_framework import serializers
from rest_framework.validators import ValidationError
from courses.mongo_utils import get_mongo_db
from bson import ObjectId
from django.contrib.auth.hashers import make_password
import re
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

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
    password = serializers.CharField(write_only=True)
    course = serializers.ListField(child=serializers.DictField(), required=False, allow_empty=True)
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

        if 'course' in representation:
            # Convert ObjectId to string in each course dictionary
            courses = representation['course']
            for course in courses:
                for key, value in course.items():
                    if isinstance(value, ObjectId):
                        course[key] = str(value)
            representation['course_id'] = courses
            del representation['course']

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['password'] = make_password(validated_data.pop('password'))
        validated_data['created_at'] = timezone.now()
        # Assuming 'course' is a list of dictionaries, convert ObjectId strings to ObjectId instances
        courses = validated_data.pop('course', [])
        for course in courses:
            for key, value in course.items():
                if key == 'id':  # Assuming 'id' is the key for ObjectId in the course dictionary
                    course[key] = ObjectId(value)
        validated_data['courses'] = courses
        result = db.customusers.insert_one(validated_data)
        return db.customusers.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        user_id = ObjectId(instance['id'])
        update_fields = {}
        for key, value in validated_data.items():
            if key == 'password':
                update_fields['password'] = make_password(value)
            elif key == 'course':
                courses = []
                for course in value:
                    course_dict = {}
                    for k, v in course.items():
                        if k == 'id':  # Assuming 'id' is the key for ObjectId in the course dictionary
                            course_dict[k] = ObjectId(v)
                        else:
                            course_dict[k] = v
                    courses.append(course_dict)
                update_fields['courses'] = courses
            else:
                update_fields[key] = value
        db.customusers.update_one({"_id": user_id}, {"$set": update_fields})
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
        validated_data['created_at'] = timezone.now()  # Use timezone.now()
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

class CourseProgressDetailsSerializer(serializers.Serializer):
    completed = serializers.IntegerField()
    total = serializers.IntegerField()

class CourseProgressResponseSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    details = serializers.DictField(child=CourseProgressDetailsSerializer())