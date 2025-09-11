import datetime
import os
import re
import pytz
from rest_framework import serializers
from bson.objectid import ObjectId

from courses.storages_backends import AssignmentStorage, CourseLibraryStorage, SubmissionStorage
from user.serializer import TeacherProfileSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .mongo_utils import get_mongo_db
# from user.serializer import TeacherProfileSerializer, CustomUserSerializer
import logging
from django.core.files.storage import default_storage # THIS WILL NOW USE S3!
from django.conf import settings 
from django.utils import timezone  # Add this import at the top


class CategorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(allow_blank=True, required=False)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.categories.insert_one(validated_data)
        return db.categories.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        category_id = ObjectId(instance['id'])
        db.categories.update_one({"_id": category_id}, {"$set": validated_data})
        return db.categories.find_one({"_id": category_id})

class VideoSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    duration = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    video_file = serializers.URLField(allow_null=True, required=False)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.videos.insert_one(validated_data)
        return db.videos.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        video_id = ObjectId(instance['id'])
        db.videos.update_one({"_id": video_id}, {"$set": validated_data})
        return db.videos.find_one({"_id": video_id})

class CourseNoteSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.DictField(allow_null=True, required=False)
    note_file = serializers.URLField(allow_null=True, required=False)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_notes.insert_one(validated_data)
        return db.course_notes.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        note_id = ObjectId(instance['id'])
        db.course_notes.update_one({"_id": note_id}, {"$set": validated_data})
        return db.course_notes.find_one({"_id": note_id})

class ModuleInCourseSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    order = serializers.IntegerField()
    video = VideoSerializer(many=True, required=False) # Changed to many=True
    course_note = CourseNoteSerializer(required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'video' in instance and isinstance(instance['video'], list):
            instance['video'] = [VideoSerializer().to_representation(item) for item in instance['video']]
        elif 'video' in instance and isinstance(instance['video'], dict):
            instance['video'] = VideoSerializer().to_representation(instance['video']) # Handle single video object as well
        if 'course_note' in instance and isinstance(instance['course_note'], dict):
            instance['course_note'] = CourseNoteSerializer().to_representation(instance['course_note'])
        return super().to_representation(instance)

class RequiredMaterialSerializer(serializers.Serializer):
    names = serializers.ListField(
        child=serializers.CharField(max_length=300),
        required=False,
        help_text="A list of required material names."
    )
    name1 = serializers.CharField(max_length=300, required=False)
    name2 = serializers.CharField(max_length=300, required=False)
    name3 = serializers.CharField(max_length=300, required=False)
    name4 = serializers.CharField(max_length=300, required=False)

    def to_representation(self, instance):
        if not instance:
            return {}

        names_list = instance.get('names', [])
        if not isinstance(names_list, list):
            names_list = []
            for i in range(1, 5):
                name_key = f'name{i}'
                if name_key in instance and instance[name_key]:
                    names_list.append(instance[name_key])

        representation = {'names': names_list}
        if '_id' in instance:
            representation['id'] = str(instance['_id'])

        return representation

    def validate(self, data):
        names_list = []
        if 'names' in data and data['names'] is not None:
            names_list.extend(data['names'])
        
        for i in range(1, 5):
            name_key = f'name{i}'
            if name_key in data and data[name_key]:
                names_list.append(data[name_key])
        
        data['names'] = list(set(names_list))
        for i in range(1, 5):
            data.pop(f'name{i}', None)
            
        return data

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.required_materials.insert_one(validated_data)
        return db.required_materials.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        materials_id = ObjectId(instance['id'])
        db.required_materials.update_one({"_id": materials_id}, {"$set": validated_data})
        return db.required_materials.find_one({"_id": materials_id})



class LearningOutcomeSerializer(serializers.Serializer):
    outcomes = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        help_text="A list of learning outcomes."
    )
    outcome1 = serializers.CharField(max_length=200, required=False)
    outcome2 = serializers.CharField(max_length=200, required=False)
    outcome3 = serializers.CharField(max_length=200, required=False)
    outcome4 = serializers.CharField(max_length=200, required=False)

    def to_representation(self, instance):
        if not instance:
            return {}
        
        outcomes_list = instance.get('outcomes', [])
        if not isinstance(outcomes_list, list):
            outcomes_list = []
            for i in range(1, 5):
                outcome_key = f'outcome{i}'
                if outcome_key in instance and instance[outcome_key]:
                    outcomes_list.append(instance[outcome_key])

        representation = {'outcomes': outcomes_list}
        if '_id' in instance:
            representation['id'] = str(instance['_id'])

        return representation

    def validate(self, data):
        outcomes_list = []
        if 'outcomes' in data and data['outcomes'] is not None:
            outcomes_list.extend(data['outcomes'])
        
        for i in range(1, 5):
            outcome_key = f'outcome{i}'
            if outcome_key in data and data[outcome_key]:
                outcomes_list.append(data[outcome_key])
        
        data['outcomes'] = list(set(outcomes_list))
        for i in range(1, 5):
            data.pop(f'outcome{i}', None)
            
        return data

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.learning_outcomes.insert_one(validated_data)
        return db.learning_outcomes.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        outcomes_id = ObjectId(instance['id'])
        db.learning_outcomes.update_one({"_id": outcomes_id}, {"$set": validated_data})
        return db.learning_outcomes.find_one({"_id": outcomes_id})

class TargetAudienceSerializer(serializers.Serializer):
    audiences = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        help_text="A list of target audiences."
    )
    audience1 = serializers.CharField(max_length=200, required=False)
    audience2 = serializers.CharField(max_length=200, required=False)
    audience3 = serializers.CharField(max_length=200, required=False)
    audience4 = serializers.CharField(max_length=200, required=False)

    def to_representation(self, instance):
        if not instance:
            return {}

        audiences_list = instance.get('audiences', [])
        if not isinstance(audiences_list, list):
            audiences_list = []
            for i in range(1, 5):
                audience_key = f'audience{i}'
                if audience_key in instance and instance[audience_key]:
                    audiences_list.append(instance[audience_key])

        representation = {'audiences': audiences_list}
        if '_id' in instance:
            representation['id'] = str(instance['_id'])

        return representation

    def validate(self, data):
        audiences_list = []
        if 'audiences' in data and data['audiences'] is not None:
            audiences_list.extend(data['audiences'])

        for i in range(1, 5):
            audience_key = f'audience{i}'
            if audience_key in data and data[audience_key]:
                audiences_list.append(data[audience_key])

        data['audiences'] = list(set(audiences_list))
        for i in range(1, 5):
            data.pop(f'audience{i}', None)
            
        return data

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.target_audience.insert_one(validated_data)
        return db.target_audience.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        audience_id = ObjectId(instance['id'])
        db.target_audience.update_one({"_id": audience_id}, {"$set": validated_data})
        return db.target_audience.find_one({"_id": audience_id})
    
class CourseIncludeSerializer(serializers.Serializer):
    include = serializers.CharField(max_length=500)
    include2 = serializers.CharField(max_length=500)
    include3 = serializers.CharField(max_length=500)
    include4 = serializers.CharField(max_length=500)
    include5 = serializers.CharField(max_length=500)
    include6 = serializers.CharField(max_length=500)
    include7 = serializers.CharField(max_length=500)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_includes.insert_one(validated_data)
        return db.course_includes.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        include_id = ObjectId(instance['id'])
        db.course_includes.update_one(
            {"_id": include_id},
            {"$set": validated_data}
        )
        return db.course_includes.find_one({"_id": include_id})

 

class CourseSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    course_image = serializers.URLField(allow_blank=True, required=False)
    preview_id = serializers.URLField(allow_blank=True, required=False)
    course_include = CourseIncludeSerializer(required=False)  # Use the new serializer
    preview_description = serializers.CharField(max_length=255, allow_blank=True, required=False)
    description = serializers.CharField()
    curriculum = ModuleInCourseSerializer(many=True, required=False) # Use the new serializer and many=True
    category = CategorySerializer()
    price = serializers.FloatField()
    original_price = serializers.FloatField()
    target_audience = serializers.JSONField(default=dict)
    learning_outcomes = serializers.JSONField(default=dict)
    instructor = 'user.serializer.TeacherProfileSerializer'
    required_materials = serializers.JSONField(default=dict)
    estimated_time = serializers.CharField(allow_blank=True, required=False)
    level = serializers.ChoiceField(choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ])

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        instructor_data = instance.get('instructor')
        representation['instructor'] = None  # Initialize as None

        if instructor_data:
            from user.serializer import TeacherProfileSerializer
            if isinstance(instructor_data, dict):
                # Case 1: Embedded Teacher Profile data
                representation['instructor'] = TeacherProfileSerializer().to_representation(instructor_data)
            elif isinstance(instructor_data, str):
                # Case 2: instructor field contains a string (potential ObjectId representation)
                try:
                    teacher_profile_id = ObjectId(instructor_data)
                    db = get_mongo_db()
                    teacher_profile = db.teacher_profiles.find_one({"_id": teacher_profile_id})
                    if teacher_profile:
                        representation['instructor'] = TeacherProfileSerializer().to_representation(teacher_profile)
                except Exception as e:
                    print(f"Error fetching TeacherProfile with ID '{instructor_data}': {e}")
            elif isinstance(instructor_data, ObjectId):
                # Case 3: instructor field contains an ObjectId
                db = get_mongo_db()
                teacher_profile = db.teacher_profiles.find_one({"_id": instructor_data})
                if teacher_profile:
                    representation['instructor'] = TeacherProfileSerializer().to_representation(teacher_profile)

        if 'category' in instance and isinstance(instance['category'], dict):
            representation['category'] = CategorySerializer().to_representation(instance['category'])
        if 'curriculum' in instance and isinstance(instance['curriculum'], list):
            representation['curriculum'] = [ModuleInCourseSerializer().to_representation(item) for item in instance['curriculum']]
        elif 'curriculum' in instance and isinstance(instance['curriculum'], dict):
            representation['curriculum'] = [ModuleInCourseSerializer().to_representation(instance['curriculum'])]
        # if 'target_audience' in instance and isinstance(instance['target_audience'], dict):
        #     representation['target_audience'] = TargetAudienceSerializer().to_representation(instance['target_audience'])
        # if 'learning_outcomes' in instance and isinstance(instance['learning_outcomes'], dict):
        #     representation['learning_outcomes'] = LearningOutcomeSerializer().to_representation(instance['learning_outcomes'])        
        # if 'required_materials' in instance and isinstance(instance['required_materials'], dict):
        #     representation['required_materials'] = RequiredMaterialSerializer().to_representation(instance['required_materials'])
        if 'course_include' in instance and isinstance(instance['course_include'], dict):
            representation['course_include'] = CourseIncludeSerializer().to_representation(instance['course_include'])

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        try:
            result = db.courses.insert_one(validated_data)
            return db.courses.find_one({"_id": result.inserted_id})
        except Exception as e:
            raise serializers.ValidationError(f"Error inserting data: {e}")

    def update(self, instance, validated_data):
        db = get_mongo_db()
        course_id = ObjectId(instance['id'])
        try:
            db.courses.update_one({"_id": course_id}, {"$set": validated_data})
            return db.courses.find_one({"_id": course_id})
        except Exception as e:
            raise serializers.ValidationError(f"Error updating data: {e}")

course_library_storage = CourseLibraryStorage()

class CourseLibraryVideoSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    video_file = serializers.FileField(
        max_length=100,
        allow_empty_file=False
    )
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        
        # Generate signed URL for the video file using your custom storage
        if 'video_file' in instance and instance['video_file']:
            instance['video_file'] = course_library_storage.url(instance['video_file'])
        
        return instance

    def create(self, validated_data):
        db = get_mongo_db()
        
        # Handle file upload to S3 using your custom storage
        video_file = validated_data.pop('video_file')
        file_name = course_library_storage.save(f'course_videos/{video_file.name}', video_file)
        
        # Store the file path in MongoDB
        validated_data['video_file'] = file_name
        validated_data['created_at'] = datetime.now()
        
        result = db.course_library_videos.insert_one(validated_data)
        return db.course_library_videos.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        video_id = ObjectId(instance['id'])
        
        # Handle file update if new file is provided
        if 'video_file' in validated_data:
            # Delete old file from S3 using your custom storage
            if 'video_file' in instance and instance['video_file']:
                course_library_storage.delete(instance['video_file'])
            
            # Save new file to S3 using your custom storage
            video_file = validated_data.pop('video_file')
            file_name = course_library_storage.save(f'course_videos/{video_file.name}', video_file)
            validated_data['video_file'] = file_name
        
        db.course_library_videos.update_one({"_id": video_id}, {"$set": validated_data})
        return db.course_library_videos.find_one({"_id": video_id})

class CourseLibrarySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    file = serializers.FileField(
        max_length=100,
        allow_null=True, required=False
    )
    url = serializers.URLField(allow_null=True, required=False)
    course = serializers.CharField()
    video = CourseLibraryVideoSerializer(many=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Handle ID conversion
        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        if 'course' in instance and instance['course']:
            try:
                course_id = ObjectId(str(instance['course']))
                db = get_mongo_db()
                course = db.courses.find_one(
                    {'_id': course_id},
                    {'name': 1, 'code': 1}
                )
                
                if course:
                    representation['course'] = {
                        'id': str(course['_id']),
                        'name': course.get('name', ''),
                        'code': course.get('code', '')
                    }
            except Exception as e:
                representation['course'] = None

        # Handle file field - check if it exists in the instance
        if 'file' in instance:
            # If file exists in instance, generate URL
            file_path = instance['file']
            if file_path:
                representation['file'] = course_library_storage.url(file_path)
        elif 'file' not in representation:
            # If file doesn't exist in instance or representation, set to None
            representation['file'] = None

        # Handle video field
        if 'video' in instance and isinstance(instance['video'], list):
            representation['video'] = [CourseLibraryVideoSerializer().to_representation(item) for item in instance['video']]
        elif 'video' in instance and isinstance(instance['video'], dict):
            representation['video'] = CourseLibraryVideoSerializer().to_representation(instance['video'])
        elif 'video' not in representation:
            representation['video'] = []

        # # Handle course_id field
        # representation['course_id'] = representation.get('course')
        # if 'course' in representation:
        #     del representation['course']

        # Handle created_at if it exists in instance but not in representation
        if 'created_at' in instance and 'created_at' not in representation:
            representation['created_at'] = instance['created_at']

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        
        # Handle file upload to S3 using your custom storage
        file = validated_data.pop('file')
        file_name = course_library_storage.save(f'course_library/{file.name}', file)
        
        # Store the file path in MongoDB
        validated_data['file'] = file_name
        validated_data['created_at'] = timezone.now()
        
        # Handle video data if provided
        videos_data = validated_data.pop('video', [])
        
        result = db.course_library.insert_one(validated_data)
        library_doc = db.course_library.find_one({"_id": result.inserted_id})
        
        # If videos were provided, create them and link to this library
        if videos_data:
            video_serializer = CourseLibraryVideoSerializer(data=videos_data, many=True)
            if video_serializer.is_valid():
                videos = video_serializer.save()
                # Update the library document with video references
                video_ids = [str(video['_id']) for video in videos]
                db.course_library.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"video": video_ids}}
                )
                # Refetch the updated document
                library_doc = db.course_library.find_one({"_id": result.inserted_id})
        
        return library_doc

    def update(self, instance, validated_data):
        db = get_mongo_db()

        # Get the library ID - handle both 'id' and '_id' cases
        if isinstance(instance, dict):
            if '_id' in instance:
                library_id = instance['_id']
            elif 'id' in instance:
                library_id = ObjectId(instance['id'])
            else:
                raise serializers.ValidationError("Invalid library instance: no ID found")
        else:
            # If instance is a model object, handle accordingly
            library_id = getattr(instance, '_id', None) or getattr(instance, 'id', None)
            if library_id and isinstance(library_id, str):
                library_id = ObjectId(library_id)

        if not library_id:
            raise serializers.ValidationError("Invalid library instance: no ID found")

        # Handle file update if needed
        uploaded_file = validated_data.pop('file', None)
        old_file = instance.get('file') if isinstance(instance, dict) else getattr(instance, 'file', None)
        new_file_name = None

        if uploaded_file:
            # Save new file
            new_file_name = course_library_storage.save(f'courselibrary/{uploaded_file.name}', uploaded_file)
            validated_data['file'] = new_file_name

            # Delete old file if it exists
            if old_file and not old_file.startswith('http'):
                try:
                    course_library_storage.delete(old_file)
                except:
                    pass  # Don't fail if old file deletion fails
                
        try:
            db.course_library.update_one({"_id": library_id}, {"$set": validated_data})
            return db.course_library.find_one({"_id": library_id})
        except Exception as e:
            # Clean up new file if update fails
            if new_file_name:
                course_library_storage.delete(new_file_name)
            raise serializers.ValidationError(f"Error updating course library: {e}")



# ... (rest of your serializers remain the same)

class LiveClassSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    course_id = serializers.CharField(write_only=True)
    course = serializers.SerializerMethodField(read_only=True)
    teacher_id = serializers.CharField(write_only=True)
    teacher = serializers.SerializerMethodField(read_only=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)
    link = serializers.URLField()
    status = serializers.CharField(read_only=True, default='scheduled')

    def get_course(self, obj):
        """Safely get course information without breaking the serializer"""
        try:
            course_id = obj.get('course_id')
            if not course_id:
                return None
                
            if isinstance(course_id, str):
                course_id = ObjectId(course_id)
            
            db = get_mongo_db()
            course = db.courses.find_one(
                {'_id': course_id},
                {'name': 1, 'code': 1}
            )
            
            if not course:
                return None
                
            return {
                'id': str(course['_id']),
                'name': course.get('name', ''),
                'code': course.get('code', '')
            }
            
        except Exception as e:
            return None

    def get_teacher(self, obj):
        """Safely get teacher information without breaking the serializer"""
        try:
            teacher_id = obj.get('teacher_id')
            if not teacher_id:
                return None
                
            if isinstance(teacher_id, str):
                teacher_id = ObjectId(teacher_id)
            
            db = get_mongo_db()
            teacher = db.teacherprofiles.find_one(
                {'_id': teacher_id},
                {'first_name': 1, 'last_name': 1, 'email': 1}
            )
            
            if not teacher:
                return None
                
            return {
                'id': str(teacher['_id']),
                'first_name': teacher.get('first_name', ''),
                'last_name': teacher.get('last_name', ''),
                'email': teacher.get('email', '')
            }
            
        except Exception as e:
            return None

    def create(self, validated_data):
        """Create a new live class with proper timezone handling"""
        try:
            db = get_mongo_db()
            
            # Get current time in Lagos timezone
            lagos_tz = pytz.timezone('Africa/Lagos')
            current_time = datetime.now(lagos_tz)
            
            # Handle start_time and end_time
            start_time = validated_data['start_time']
            end_time = validated_data['end_time']
            
            # If times are naive, assume they're in Lagos timezone
            if timezone.is_naive(start_time):
                start_time = lagos_tz.localize(start_time)
            else:
                # Convert to Lagos timezone if it's in another timezone
                start_time = start_time.astimezone(lagos_tz)
                
            if timezone.is_naive(end_time):
                end_time = lagos_tz.localize(end_time)
            else:
                end_time = end_time.astimezone(lagos_tz)
            
            live_class_data = {
                'course_id': ObjectId(validated_data['course_id']),
                'teacher_id': ObjectId(validated_data['teacher_id']),
                'start_time': start_time,
                'end_time': end_time,
                'link': validated_data['link'],
                'created_at': current_time,
                'status': 'scheduled',
                'participants': []
            }
            
            result = db.liveclasss.insert_one(live_class_data)
            live_class_data['_id'] = result.inserted_id
            live_class_data['id'] = str(result.inserted_id)
            
            return live_class_data
            
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create live class: {str(e)}")

    def update(self, instance, validated_data):
        """Update an existing live class with proper timezone handling"""
        try:
            db = get_mongo_db()
            
            updates = {}
            lagos_tz = pytz.timezone('Africa/Lagos')
            
            if 'course_id' in validated_data:
                updates['course_id'] = ObjectId(validated_data['course_id'])
            if 'teacher_id' in validated_data:
                updates['teacher_id'] = ObjectId(validated_data['teacher_id'])
            if 'start_time' in validated_data:
                start_time = validated_data['start_time']
                if timezone.is_naive(start_time):
                    start_time = lagos_tz.localize(start_time)
                else:
                    start_time = start_time.astimezone(lagos_tz)
                updates['start_time'] = start_time
            if 'end_time' in validated_data:
                end_time = validated_data['end_time']
                if timezone.is_naive(end_time):
                    end_time = lagos_tz.localize(end_time)
                else:
                    end_time = end_time.astimezone(lagos_tz)
                updates['end_time'] = end_time
            if 'link' in validated_data:
                updates['link'] = validated_data['link']
            
            if updates:
                db.liveclasss.update_one(
                    {'_id': ObjectId(instance['_id'])},
                    {'$set': updates}
                )
                
                instance.update(updates)
            
            return instance
            
        except Exception as e:
            raise serializers.ValidationError(f"Failed to update live class: {str(e)}")

    def to_representation(self, instance):
        """Convert MongoDB document to API response format"""
        representation = super().to_representation(instance)
        
        # Ensure ID is always present
        if '_id' in instance and 'id' not in representation:
            representation['id'] = str(instance['_id'])
        
        # Remove internal MongoDB fields
        representation.pop('_id', None)
        representation.pop('course_id', None)
        representation.pop('teacher_id', None)
        
        # Add additional fields if needed
        if 'status' in instance:
            representation['status'] = instance['status']
        if 'participants' in instance:
            representation['participants'] = instance['participants']
        if 'created_at' in instance:
            representation['created_at'] = instance['created_at']
        
        return representation

    def validate_course_id(self, value):
        """Validate that course exists"""
        try:
            db = get_mongo_db()
            course = db.courses.find_one({'_id': ObjectId(value)})
            if not course:
                raise serializers.ValidationError("Course does not exist")
            return value
        except:
            raise serializers.ValidationError("Invalid course ID format")

    def validate_teacher_id(self, value):
        """Validate that teacher exists"""
        try:
            db = get_mongo_db()
            teacher = db.teacherprofiles.find_one({'_id': ObjectId(value)})
            if not teacher:
                raise serializers.ValidationError("Teacher does not exist")
            return value
        except:
            raise serializers.ValidationError("Invalid teacher ID format")

    def validate(self, data):
        """Validate that end_time is after start_time"""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data



class EventSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    icon = serializers.ImageField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200)
    image = serializers.URLField()
    event_excerpt = serializers.CharField()
    date = serializers.CharField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    timezone = serializers.CharField(max_length=50, default='EST')
    is_active = serializers.BooleanField(default=True)
    instructor = serializers.CharField(max_length=100)
    instructor_info = serializers.CharField()
    workshop = serializers.JSONField(default=dict)
    course = CourseSerializer(required=False, allow_null=True)
    who_can_attend = serializers.CharField()
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    django_id = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        # Handle MongoDB _id field
        if '_id' in instance:
            if isinstance(instance['_id'], dict) and '$oid' in instance['_id']:
                instance['id'] = instance['_id']['$oid']
            else:
                instance['id'] = str(instance['_id'])
            del instance['_id']
        
        # Convert course data if it exists
        if 'course' in instance and isinstance(instance['course'], dict):
            if '_id' in instance['course']:
                instance['course']['id'] = str(instance['course']['_id'])
                del instance['course']['_id']
        
        return super().to_representation(instance)

    def to_internal_value(self, data):
        data = data.copy()
        
        # Handle event ID
        if 'id' in data:
            if isinstance(data['id'], dict) and '$oid' in data['id']:
                data['_id'] = ObjectId(data['id']['$oid'])
                del data['id']
        
        # Handle course ID
        if 'course' in data and data['course']:
            if isinstance(data['course'], dict) and 'id' in data['course']:
                if isinstance(data['course']['id'], dict) and '$oid' in data['course']['id']:
                    data['course']['_id'] = ObjectId(data['course']['id']['$oid'])
                    del data['course']['id']
        
        return super().to_internal_value(data)

    def create(self, validated_data):
        db = get_mongo_db()
        
        # Handle course data
        course_data = validated_data.pop('course', None)
        if course_data:
            validated_data['course'] = course_data
        
        # Prepare MongoDB document
        mongo_data = {
            **validated_data,
            'date': validated_data.get('date').isoformat(),
            'start_time': validated_data.get('start_time').isoformat(),
            'end_time': validated_data.get('end_time').isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = db.events.insert_one(mongo_data)
        return db.events.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        event_id = ObjectId(instance.get('id', instance.get('_id')))
        
        # Handle course update
        if 'course' in validated_data:
            if validated_data['course'] is None:
                # Remove course reference
                db.events.update_one(
                    {"_id": event_id},
                    {"$unset": {"course": ""}}
                )
            else:
                # Update course data
                db.events.update_one(
                    {"_id": event_id},
                    {"$set": {"course": validated_data['course']}}
                )
        
        # Update other fields
        update_data = {
            k: v for k, v in validated_data.items()
            if k != 'course'
        }
        
        if update_data:
            db.events.update_one(
                {"_id": event_id},
                {"$set": {
                    **update_data,
                    'updated_at': datetime.now().isoformat()
                }}
            )
        
        return db.events.find_one({"_id": event_id})

logger = logging.getLogger(__name__)

assignment_storage = AssignmentStorage()

class AssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True, source='_id')
    course = serializers.CharField(max_length=24, required=False)
    teacher = serializers.CharField(max_length=24, required=False)
    title = serializers.CharField(max_length=200)
    total_marks = serializers.IntegerField(default=100)
    description = serializers.CharField()
    due_date = serializers.DateTimeField()
    file = serializers.FileField(
        max_length=100,
        allow_null=True, required=False
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Handle ID conversion safely
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        
        # Handle course data
        if 'course' in instance and instance['course']:
            try:
                course_id = ObjectId(str(instance['course']))
                db = get_mongo_db()
                course = db.courses.find_one(
                    {'_id': course_id},
                    {'name': 1, 'code': 1}
                )
                
                if course:
                    representation['course'] = {
                        'id': str(course['_id']),
                        'name': course.get('name', ''),
                        'code': course.get('code', '')
                    }
                else:
                    representation['course'] = None
            except Exception as e:
                representation['course'] = None

        # Handle teacher data
        if 'teacher' in instance and instance['teacher']:
            try:
                teacher_id = ObjectId(str(instance['teacher']))
                db = get_mongo_db()
                teacher = db.teacherprofiles.find_one(
                    {'_id': teacher_id},
                    {'first_name': 1, 'last_name': 1, 'email': 1, 'profile_picture': 1}
                )
                
                if teacher:
                    representation['teacher'] = {
                        'id': str(teacher['_id']),
                        'first_name': teacher.get('first_name', ''),
                        'last_name': teacher.get('last_name', ''),
                        'email': teacher.get('email', ''),
                        'profile_picture': teacher.get('profile_picture', '')
                    }
                else:
                    representation['teacher'] = None
            except Exception as e:
                representation['teacher'] = None
        
        # Handle file field
        if 'file' in instance and instance.get('file'):
            # Check if it's already a URL or a file path
            if instance['file'].startswith('http'):
                representation['file'] = instance['file']
            else:
                representation['file'] = assignment_storage.url(instance['file'])
        else:
            representation['file'] = None
        
        return representation
    
    def create(self, validated_data):
        db = get_mongo_db()
        

        # Use course_id directly. Convert it to ObjectId.
        if 'course_id' in validated_data:
            validated_data['course'] = ObjectId(validated_data.pop('course_id'))

        # Handle file upload to S3 using your custom storage
        file = validated_data.pop('file')
        file_name = assignment_storage.save(f'assignments/{file.name}', file)


        validated_data['file'] = file_name
        validated_data['created_at'] = timezone.now()

        try:
            result = db.make_assignments.insert_one(validated_data)
            return db.make_assignments.find_one({"_id": result.inserted_id})
        except Exception as e:
            # Clean up file if insertion fails
            if file_name:
                course_library_storage.delete(file_name)
            raise serializers.ValidationError(f"Error creating assignment: {e}")
        

    def update(self, instance, validated_data):
        db = get_mongo_db()

        # FIX: Handle different types of ID
        if isinstance(instance, dict) and 'id' in instance:
            assignment_id_str = str(instance['id'])  # Convert to string first
            assignment_id = ObjectId(assignment_id_str)
        elif isinstance(instance, dict) and '_id' in instance:
            assignment_id = instance['_id']
        else:
            raise serializers.ValidationError("Invalid assignment instance")

        file = validated_data.pop('file')
        file_name = course_library_storage.save(f'assignments/{file.name}', file)
        
        # Store the file path in MongoDB
        validated_data['file'] = file_name
        validated_data['created_at'] = timezone.now()

        # Handle file update using custom storage
        

        # Handle course_id conversion
        if 'course_id' in validated_data:
            validated_data['course_id'] = ObjectId(validated_data['course_id'])

        # Handle teacher field - REMOVE THIS since teacher is read-only now
        validated_data.pop('teacher', None)  # Remove teacher data from update

        
        db.make_assignments.update_one({"_id": assignment_id}, {"$set": validated_data})

            

submission_storage = SubmissionStorage()
class SubmissionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    assignment_id = serializers.CharField(write_only=True)
    assignment = serializers.SerializerMethodField(read_only=True)
    student_id = serializers.CharField(write_only=True, required=False)
    student = serializers.SerializerMethodField(read_only=True)
    submission_date = serializers.DateTimeField(read_only=True)
    marks_obtained = serializers.IntegerField(required=False, default=0)
    feedback = serializers.CharField(required=False, allow_blank=True)
    marked_by_id = serializers.CharField(required=False, allow_null=True, write_only=True)
    marked_by = serializers.SerializerMethodField(read_only=True)
    file = serializers.FileField(allow_null=True, required=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert MongoDB ObjectId to string
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        
        # Handle file URL generation
        file_val = instance.get('file')
        if file_val:
            if isinstance(file_val, str) and file_val.startswith('http'):
                representation['file'] = file_val
            else:
                representation['file'] = submission_storage.url(file_val)
        else:
            representation['file'] = None
        
        return representation

    def get_assignment(self, obj):
        return self._get_document(obj, 'assignment', 'make_assignments', ['title', 'course'])

    def get_student(self, obj):
        return self._get_document(obj, 'student', 'customusers', ['first_name', 'last_name', 'email'])

    def get_marked_by(self, obj):
        return self._get_document(obj, 'marked_by', 'teacherprofiles', ['first_name', 'last_name', 'email'])

    def _get_document(self, obj, field, collection, fields):
        """Helper to fetch related document from MongoDB"""
        if field not in obj or not obj[field]:
            return None
        try:
            doc_id = ObjectId(str(obj[field]))
            db = get_mongo_db()
            projection = {f: 1 for f in fields}
            document = db[collection].find_one({'_id': doc_id}, projection)
            if not document:
                return None
            result = {'id': str(document['_id'])}
            for f in fields:
                result[f] = document.get(f)
                if f == 'course' and result[f]:
                    result[f] = str(result[f])  # Convert course ObjectId to string
            return result
        except Exception:
            return None

    def create(self, validated_data):
        db = get_mongo_db()
        request = self.context.get('request')

        # Convert assignment_id to ObjectId
        validated_data['assignment'] = ObjectId(validated_data.pop('assignment_id'))

        # Set student from request user
        if request and hasattr(request, 'user'):
            try:
                # Get student ID based on your user model structure
                student_id = str(request.user.studentprofile.id)
                validated_data['student'] = ObjectId(student_id)
            except AttributeError:
                raise serializers.ValidationError("User doesn't have a student profile")

        # Handle file upload
        file = validated_data.get('file')
        if file:
            try:
                # Generate a unique filename
                file_name = f"submissions/{timezone.now().strftime('%Y%m%d_%H%M%S')}_{file.name}"
                # Save the file using the storage instance
                saved_name = submission_storage.save(file_name, file)
                validated_data['file'] = saved_name
            except Exception as e:
                raise serializers.ValidationError(f"Error saving file: {str(e)}")

        validated_data['submission_date'] = timezone.now()

        # Insert into database
        try:
            result = db.submissions.insert_one(validated_data)
            return db.submissions.find_one({"_id": result.inserted_id})
        except Exception as e:
            # Clean up file if insertion fails
            if 'file' in validated_data:
                try:
                    submission_storage.delete(validated_data['file'])
                except:
                    pass  # Don't fail if file deletion fails
            raise serializers.ValidationError(f"Error creating submission: {str(e)}")

    def update(self, instance, validated_data):
        db = get_mongo_db()
        submission_id = instance.get('_id')
        
        if not submission_id:
            raise serializers.ValidationError("Invalid submission instance")
        
        # Handle file update
        new_file = validated_data.get('file')
        old_file = instance.get('file')
        if new_file:
            # Save new file
            new_file_name = submission_storage.save(f'submissions/{new_file.name}', new_file)
            validated_data['file'] = new_file_name
            # Delete old file if it exists
            if old_file and not old_file.startswith('http'):
                try:
                    submission_storage.delete(old_file)
                except Exception:
                    pass  # Log error if needed
        
        # Convert IDs to ObjectIds if present
        id_fields = ['assignment_id', 'student_id', 'marked_by_id']
        for field in id_fields:
            if field in validated_data:
                new_field_name = field.replace('_id', '')
                validated_data[new_field_name] = ObjectId(validated_data.pop(field))
        
        # Update database
        try:
            db.submissions.update_one({"_id": submission_id}, {"$set": validated_data})
            return db.submissions.find_one({"_id": submission_id})
        except Exception as e:
            # Clean up new file if update fails
            if new_file:
                submission_storage.delete(validated_data['file'])
            raise serializers.ValidationError(f"Error updating submission: {str(e)}")

# class CourseOrderItemSerializer(serializers.Serializer):
#     id = serializers.CharField(read_only=True)
#     order_id = serializers.CharField()
#     course_id = serializers.CharField()
#     price = serializers.FloatField()
#     course_name = serializers.SerializerMethodField()

#     def get_course_name(self, instance):
#         db = get_mongo_db()
#         course = db.courses.find_one({"_id": ObjectId(instance['course_id'])})
#         return course.get('name') if course else None

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         if '_id' in instance:
#             representation['id'] = str(instance['_id'])
#         return representation

#     def create(self, validated_data):
#         db = get_mongo_db()
#         result = db.course_order_items.insert_one(validated_data)
#         return db.course_order_items.find_one({"_id": result.inserted_id})

#     def update(self, instance, validated_data):
#         db = get_mongo_db()
#         item_id = ObjectId(instance['id'])
#         db.course_order_items.update_one({"_id": item_id}, {"$set": validated_data})
#         return db.course_order_items.find_one({"_id": item_id})

# class CourseOrderSerializer(serializers.Serializer):
#     id = serializers.CharField(read_only=True)
#     user_id = serializers.CharField()
#     total_price = serializers.FloatField(read_only=True)
#     payment_status = serializers.CharField(default='pending')
#     created_at = serializers.DateTimeField(read_only=True)
#     updated_at = serializers.DateTimeField(read_only=True)
#     order_items = CourseOrderItemSerializer(many=True, read_only=True)

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         if '_id' in instance:
#             representation['id'] = str(instance['_id'])
#         return representation

#     def create(self, validated_data):
#         db = get_mongo_db()
#         validated_data['created_at'] = datetime.datetime.utcnow()
#         validated_data['updated_at'] = datetime.datetime.utcnow()
#         result = db.course_orders.insert_one(validated_data)
#         return db.course_orders.find_one({"_id": result.inserted_id})

#     def update(self, instance, validated_data):
#         db = get_mongo_db()
#         validated_data['updated_at'] = datetime.datetime.utcnow()
#         order_id = ObjectId(instance['id'])
#         db.course_orders.update_one({"_id": order_id}, {"$set": validated_data})
#         return db.course_orders.find_one({"_id": order_id})




class CompletionCertificateSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    certificate_url = serializers.URLField()
    issued_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.completion_certificates.insert_one(validated_data)
        return db.completion_certificates.find_one({"_id": result.inserted_id})


class EventRegistrationSerializer(serializers.Serializer):
    COURSE_CHOICES = [
        ('AML/KYC Compliance', 'AML/KYC Compliance'),
        ('Business Analysis & Project Management', 'Business Analysis & Project Management'),
        ('Cybersecurity', 'Cybersecurity'),
        ('Data Analysis', 'Data Analysis'),
        
    ]
    
    course_name = serializers.ChoiceField(
        choices=COURSE_CHOICES,
        required=True
    )
    email = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=False, max_length=100)
    phone_number = serializers.CharField(required=False)
    whatsapp_number = serializers.CharField(required=False)
    message = serializers.CharField(required=False, allow_blank=True)

    

    def validate_email(self, value):
        try:
            validate_email(value)
            return value.lower()  # Normalize email to lowercase
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address")

    def validate_phone_number(self, value):
        if value:  # Only validate if phone number is provided
            # Allow +, numbers, and whitespace/punctuation that will be removed later
            if not re.match(r'^[\d\s+\-()]{6,20}$', value):
                raise serializers.ValidationError(
                    "Enter a valid phone number with country code (e.g. +44...)")
        return value

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name cannot be empty")
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Last name cannot be empty")
        return value

    def validate(self, data):
        """
        Optional: Add any cross-field validation here
        """
        return data
    

class ConsultationSerializer(serializers.Serializer):

    COURSE_CHOICES = [
    ('AML/KYC Compliance', 'AML/KYC Compliance'),
    ('Business Analysis & Project Management', 'Business Analysis & Project Management'),
    ('Cybersecurity', 'Cybersecurity'),
    ('Data Analysis', 'Data Analysis'),
    ]
    
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    whatsappNumber = serializers.CharField(max_length=20, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    course = serializers.ChoiceField(choices=COURSE_CHOICES)

    

    def validate_email(self, value):
        try:
            validate_email(value)
            return value.lower()  # Normalize email to lowercase
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address")

    def validate_whatsappNumber(self, value):
        if value and not re.match(r'^\+[1-9]\d{1,14}$', value):
            raise serializers.ValidationError("WhatsApp number must be in international format (e.g., +1234567890)")
        return value
    
    def validate_phone_number(self, value):
        if value and not re.match(r'^\+[1-9]\d{1,14}$', value):
            raise serializers.ValidationError("Phone number must be in international format (e.g., +1234567890)")
        return value

    def validate_firstName(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name cannot be empty")
        return value

    def validate_lastName(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Last name cannot be empty")
        return value

    def validate(self, data):
        """
        Optional: Add any cross-field validation here
        """
        return data