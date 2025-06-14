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

class ProgressItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    # Use Field.empty to allow dynamic keys based on 'type'
    completed = serializers.IntegerField(required=False, default=0) # for videos
    opened = serializers.IntegerField(required=False, default=0)    # for notes
    submitted = serializers.IntegerField(required=False, default=0) # for assignments
    viewed = serializers.IntegerField(required=False, default=0)    # for PDFs
    total = serializers.IntegerField(required=False, default=0)

    def get_completed(self, obj):
        # Only return 'completed' if the type is 'videos'
        if obj.get('type') == 'videos':
            return obj.get('completed', 0)
        return None # Return None or don't return anything if not applicable

    def get_opened(self, obj):
        # Only return 'opened' if the type is 'course_notes'
        if obj.get('type') == 'course_notes':
            return obj.get('opened', 0)
        return None

    def get_submitted(self, obj):
        # Only return 'submitted' if the type is 'assignments'
        if obj.get('type') == 'assignments':
            return obj.get('submitted', 0)
        return None

    def get_viewed(self, obj):
        # Only return 'viewed' if the type is 'blog_pdfs'
        if obj.get('type') == 'blog_pdfs':
            return obj.get('viewed', 0)
        return None

    # This method ensures that fields with None values are excluded from the output
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Remove fields that returned None (i.e., not applicable for this type)
        fields_to_remove = []
        for field_name in ['completed', 'opened', 'submitted', 'viewed']:
            if ret.get(field_name) is None:
                fields_to_remove.append(field_name)
        
        for field_name in fields_to_remove:
            ret.pop(field_name)
        
        return ret

# --- MODIFIED: CourseProgressResponseSerializer ---
class CourseProgressResponseSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    progress_percentage = serializers.IntegerField()

    # The 'details' field is now a ListField of ProgressItemSerializer
    details = serializers.ListField(
        child=ProgressItemSerializer()
    )

    # We no longer need get_videos, get_course_notes, etc.,
    # nor the complex to_representation logic for 'details'
    # as ListField handles it.
    # So, REMOVE all get_X methods and the to_representation method
    # from CourseProgressResponseSerializer.

# --- CourseProgressSerializer (for storing data in MongoDB) ---
# You also need to decide how you're storing this in MongoDB.
# If you want it stored as an array in the `course_progress_records` collection,
# then `details` in `CourseProgressSerializer` should also become a `ListField`.

class CourseProgressSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True, required=False)
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    
    # Change this to ListField if you want to store it as an array in MongoDB
    details = serializers.ListField(
        child=ProgressItemSerializer() # Using the new generic item serializer
    )
    last_updated = serializers.DateTimeField(required=False)

    # ... (create and update methods - they should work fine with ListField now) ...
    def create(self, validated_data):
        db = get_mongo_db()
        progress_collection = db.course_progress_records
        validated_data['last_updated'] = timezone.now()
        validated_data['user_id'] = ObjectId(validated_data['user_id'])
        validated_data['course_id'] = ObjectId(validated_data['course_id'])

        result = progress_collection.insert_one(validated_data)
        created_doc = progress_collection.find_one({"_id": result.inserted_id})
        if created_doc:
            created_doc['_id'] = str(created_doc['_id'])
            created_doc['user_id'] = str(created_doc['user_id'])
            created_doc['course_id'] = str(created_doc['course_id'])
        return created_doc

    def update(self, instance, validated_data):
        db = get_mongo_db()
        progress_collection = db.course_progress_records
        validated_data['last_updated'] = timezone.now()

        instance_id = instance.get('_id')
        if not isinstance(instance_id, ObjectId):
            instance_id = ObjectId(instance_id)

        if 'user_id' in validated_data and isinstance(validated_data['user_id'], str):
             validated_data['user_id'] = ObjectId(validated_data['user_id'])
        if 'course_id' in validated_data and isinstance(validated_data['course_id'], str):
             validated_data['course_id'] = ObjectId(validated_data['course_id'])

        progress_collection.update_one(
            {"_id": instance_id},
            {"$set": validated_data}
        )
        updated_doc = progress_collection.find_one({"_id": instance_id})
        if updated_doc:
            updated_doc['_id'] = str(updated_doc['_id'])
            updated_doc['user_id'] = str(updated_doc['user_id'])
            updated_doc['course_id'] = str(updated_doc['course_id'])
        return updated_doc


# --- CourseProgressSerializer (for storing data in MongoDB) ---
# This remains largely the same, its DictField for 'details' is fine here
# as it handles the raw dictionary data for storage.
class CourseProgressSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True, required=False)
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    details = serializers.DictField() # This DictField is fine here
    last_updated = serializers.DateTimeField(required=False)

    def create(self, validated_data):
        db = get_mongo_db()
        progress_collection = db.course_progress_records # Ensure this collection name is consistent
        validated_data['last_updated'] = timezone.now()
        validated_data['user_id'] = ObjectId(validated_data['user_id'])
        validated_data['course_id'] = ObjectId(validated_data['course_id'])

        result = progress_collection.insert_one(validated_data)
        created_doc = progress_collection.find_one({"_id": result.inserted_id})
        # Convert ObjectIds back to strings for serializer output
        if created_doc:
            created_doc['_id'] = str(created_doc['_id'])
            created_doc['user_id'] = str(created_doc['user_id'])
            created_doc['course_id'] = str(created_doc['course_id'])
        return created_doc

    def update(self, instance, validated_data):
        db = get_mongo_db()
        progress_collection = db.course_progress_records # Ensure this collection name is consistent
        validated_data['last_updated'] = timezone.now()

        instance_id = instance.get('_id')
        if not isinstance(instance_id, ObjectId):
            instance_id = ObjectId(instance_id)

        if 'user_id' in validated_data and isinstance(validated_data['user_id'], str):
             validated_data['user_id'] = ObjectId(validated_data['user_id'])
        if 'course_id' in validated_data and isinstance(validated_data['course_id'], str):
             validated_data['course_id'] = ObjectId(validated_data['course_id'])

        progress_collection.update_one(
            {"_id": instance_id},
            {"$set": validated_data}
        )
        updated_doc = progress_collection.find_one({"_id": instance_id})
        if updated_doc:
            updated_doc['_id'] = str(updated_doc['_id'])
            updated_doc['user_id'] = str(updated_doc['user_id'])
            updated_doc['course_id'] = str(updated_doc['course_id'])
        return updated_doc

# --- CourseProgressRecordSerializer (for TeacherCourseProgressOverview) ---
# This serializer should directly mirror the structure of documents in `course_progress_records`
# and then use to_representation to format it for the API output.
class CourseProgressRecordSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id', read_only=True)
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    course_name = serializers.CharField(required=False, allow_blank=True)
    student_username = serializers.CharField(required=False, allow_blank=True)
    progress_percentage = serializers.IntegerField()
    last_updated_at = serializers.DateTimeField()

    # These fields refer to the keys *within* the 'details' dictionary of the MongoDB document
    # Using source='details.videos' allows direct mapping from nested MongoDB fields.
    details = serializers.ListField(
        child=ProgressItemSerializer() # Using the new generic item serializer
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        details_data = {}
        # Safely pop and add to details_data, only if present in representation
        if 'videos' in representation and representation['videos'] is not None:
            details_data['videos'] = representation.pop('videos')
        if 'course_notes' in representation and representation['course_notes'] is not None:
            details_data['course_notes'] = representation.pop('course_notes')
        if 'assignments' in representation and representation['assignments'] is not None:
            details_data['assignments'] = representation.pop('assignments')
        if 'blog_pdfs' in representation: # blog_pdfs might be empty if no PDFs
            details_data['blog_pdfs'] = representation.pop('blog_pdfs')

        representation['details'] = details_data
        return representation