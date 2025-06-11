# serializers.py

from rest_framework import serializers
from rest_framework.validators import ValidationError
from courses.mongo_utils import get_mongo_db
from bson import ObjectId
from django.contrib.auth.hashers import make_password
import re
from django.utils import timezone
import logging
from django.db import models # Add this line
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
        # Determine if the instance is a Django model object or a raw MongoDB dict
        # The error occurs when `instance` is a Django `CustomUser` object after `login(request, user)`
        if isinstance(instance, models.Model): # Check if it's a Django model instance
            representation = {
                "id": str(instance.id),
                "username": instance.username,
                "email": instance.email,
                "first_name": instance.first_name,
                "last_name": instance.last_name,
                "role": instance.role,
                "phone_number": instance.phone_number,
                "profile_pic": instance.profile_pic.url if instance.profile_pic else None,
                "date_joined": instance.date_joined.isoformat(),
                # Process the ManyToManyField 'course' here
                "course": [course.to_dict() for course in instance.course.all()], # <--- CRITICAL CHANGE HERE
            }
            # Remove password field if it exists, as it's write_only
            if 'password' in representation:
                del representation['password']

        else: # Assume it's a MongoDB dictionary
            representation = super().to_representation(instance)

            if '_id' in instance:
                representation['id'] = str(instance['_id'])
            # Ensure 'id' is present and not '_id'
            elif hasattr(instance, '_id'): # If it's a BSON document like object
                representation['id'] = str(instance._id)

            if '_id' in representation:
                del representation['_id']

            # Handle the 'course' field for MongoDB documents
            if 'course' in representation and isinstance(representation['course'], list):
                course_data = []
                for course_item in representation['course']:
                    # Assuming course_item is already a dict from MongoDB
                    # Make sure 'id' is a string if it was ObjectId in Mongo
                    course_dict = {
                        'id': str(course_item['_id']) if '_id' in course_item else None, # Convert ObjectId to string
                        'name': course_item.get('name'),
                        'course_image': course_item.get('course_image'),
                        'preview_id': course_item.get('preview_id'),
                        'preview_description': course_item.get('preview_description'),
                        'description': course_item.get('description'),
                        'category': course_item.get('category'),
                        'price': course_item.get('price'),
                        'target_audience': course_item.get('target_audience'),
                        'learning_outcomes': course_item.get('learning_outcomes'),
                        'instructor': course_item.get('instructor'),
                        'required_materials': course_item.get('required_materials'),
                        'estimated_time': course_item.get('estimated_time'),
                        'level': course_item.get('level'),
                    }
                    course_data.append(course_dict)
                representation['course'] = course_data
            else:
                representation['course'] = [] # Ensure course is an empty list if not found or not a list

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['password'] = make_password(validated_data.pop('password'))
        validated_data['date_joined'] = timezone.now() # Use date_joined to match model
        
        courses_data = validated_data.pop('course', []) # Use courses_data to avoid conflict with model field
        processed_courses_for_mongo = []
        for course_item in courses_data:
            # Assuming 'id' in incoming course data is the MongoDB _id string for existing courses
            if 'id' in course_item and ObjectId.is_valid(course_item['id']):
                course_item['_id'] = ObjectId(course_item.pop('id')) # Convert 'id' to '_id' ObjectId for Mongo
            processed_courses_for_mongo.append(course_item)
        
        validated_data['course'] = processed_courses_for_mongo # Store as 'course' in MongoDB
        
        result = db.customusers.insert_one(validated_data)
        # When creating, return the MongoDB document for serialization
        return db.customusers.find_one({"_id": result.inserted_id})


    def update(self, instance, validated_data):
        db = get_mongo_db()
        
        # Determine if `instance` is a Django model or a MongoDB dict
        if isinstance(instance, models.Model):
            user_id = ObjectId(instance.id) # Get _id from Django model's id
        else:
            user_id = ObjectId(instance['id']) # Get _id from MongoDB dict's 'id' field

        update_fields = {}
        for key, value in validated_data.items():
            if key == 'password':
                update_fields['password'] = make_password(value)
            elif key == 'course':
                courses_for_mongo = []
                for course_item in value:
                    course_dict = {}
                    for k, v in course_item.items():
                        if k == 'id' and ObjectId.is_valid(v):
                            course_dict['_id'] = ObjectId(v) # Convert 'id' to '_id' ObjectId for Mongo
                        else:
                            course_dict[k] = v
                    courses_for_mongo.append(course_dict)
                update_fields['course'] = courses_for_mongo # Store as 'course' in MongoDB
            else:
                update_fields[key] = value
        
        db.customusers.update_one({"_id": user_id}, {"$set": update_fields})
        return db.customusers.find_one({"_id": user_id})
    

class TeacherLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    token = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True) # If you return refresh token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Use Django's authenticate function, which will call your MongoAuthBackend
            user = authenticate(request=self.context.get('request'), email=email, password=password)

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

import logging
logger = logging.getLogger(__name__)

db = get_mongo_db()
get_teacher_profile_collection = db['teacherprofiles']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Simplified TokenObtainPairSerializer that focuses on authentication
    and token generation. The custom logic moves to the view.
    """
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    # The validate method will now just call super().validate
    # The self.user will be populated, and its _mongo_doc should be present
    # due to the backend. The rest of the custom logic moves to the view.
    # We still keep this method to benefit from Simple JWT's internal authentication flow.
    def validate(self, attrs):
        data = super().validate(attrs) # This performs authentication and populates self.user
        
        # At this point, self.user should be an instance of CustomUser
        # and should have the _mongo_doc attribute attached by MongoAuthBackend.
        # We can add a quick debug check here if needed, but the main checks
        # will now occur in the view.

        # logger.debug(f"DEBUG (Serializer Validate): User: {self.user.email}, _mongo_doc present: {hasattr(self.user, '_mongo_doc')}")
        
        return data

        

    

class TeacherProfileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField()
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    password = serializers.CharField(write_only=True)
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
        result = db.teacherprofiles.insert_one(validated_data)
        return db.teacherprofiles.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        profile_id = ObjectId(instance['id'])
        db.teacherprofiles.update_one({"_id": profile_id}, {"$set": validated_data})
        return db.teacherprofiles.find_one({"_id": profile_id})

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