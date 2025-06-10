import datetime
from rest_framework import serializers
from bson.objectid import ObjectId
from .mongo_utils import get_mongo_db
# from user.serializer import TeacherProfileSerializer, CustomUserSerializer
import logging


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
    description = serializers.CharField()
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
    note_file = serializers.FileField(allow_null=True, required=False)

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
    name1 = serializers.CharField(max_length=300)
    name2 = serializers.CharField(max_length=300)
    name3 = serializers.CharField(max_length=300)
    name4 = serializers.CharField(max_length=300)

    def to_representation(self, instance):
        if instance is None:
            return {}
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

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
    outcome1 = serializers.CharField(max_length=200)
    outcome2 = serializers.CharField(max_length=200)
    outcome3 = serializers.CharField(max_length=200)
    outcome4 = serializers.CharField(max_length=200)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

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
    audience1 = serializers.CharField(max_length=200)
    audience2 = serializers.CharField(max_length=200)
    audience3 = serializers.CharField(max_length=200)
    audience4 = serializers.CharField(max_length=200)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.target_audience.insert_one(validated_data)
        return db.target_audience.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        audience_id = ObjectId(instance['id'])
        db.target_audience.update_one({"_id": audience_id}, {"$set": validated_data})
        return db.target_audience.find_one({"_id": audience_id})



class CourseSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    course_image = serializers.URLField(allow_blank=True, required=False)
    preview_id = serializers.CharField(allow_blank=True, required=False, max_length=200)
    preview_description = serializers.CharField(max_length=255, allow_blank=True, required=False)
    description = serializers.CharField()
    curriculum = ModuleInCourseSerializer(many=True, required=False) # Use the new serializer and many=True
    category = CategorySerializer()
    price = serializers.FloatField()
    target_audience = TargetAudienceSerializer(required=False)
    learning_outcomes = LearningOutcomeSerializer(required=False)
    instructor = 'user.serializer.TeacherProfileSerializer'
    required_materials = RequiredMaterialSerializer(required=False)
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
        if 'target_audience' in instance and isinstance(instance['target_audience'], dict):
            representation['target_audience'] = TargetAudienceSerializer().to_representation(instance['target_audience'])
        if 'learning_outcomes' in instance and isinstance(instance['learning_outcomes'], dict):
            representation['learning_outcomes'] = LearningOutcomeSerializer().to_representation(instance['learning_outcomes'])        
        if 'required_materials' in instance and isinstance(instance['required_materials'], dict):
            representation['required_materials'] = RequiredMaterialSerializer().to_representation(instance['required_materials'])

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

class CourseLibraryVideoSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    video_file = serializers.CharField(allow_null=True, required=False)
    video_id = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        return instance

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_library_videos.insert_one(validated_data)
        return db.course_library_videos.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        video_id = ObjectId(instance['id'])
        db.course_library_videos.update_one({"_id": video_id}, {"$set": validated_data})
        return db.course_library_videos.find_one({"_id": video_id})

class CourseLibrarySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    file = serializers.CharField(allow_null=True, required=False)
    url = serializers.URLField(allow_null=True, required=False)
    course = serializers.CharField()
    video = CourseLibraryVideoSerializer(many=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        if 'video' in instance and isinstance(instance['video'], list):
            representation['video'] = [CourseLibraryVideoSerializer().to_representation(item) for item in instance['video']]
        elif 'video' in instance and isinstance(instance['video'], dict):
            representation['video'] = CourseLibraryVideoSerializer().to_representation(instance['video'])

        representation['course_id'] = representation.get('course')
        if 'course' in representation:
            del representation['course']

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_library.insert_one(validated_data)
        return db.course_library.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        library_id = ObjectId(instance['id'])
        db.course_library.update_one({"_id": library_id}, {"$set": validated_data})
        return db.course_library.find_one({"_id": library_id})



# ... (rest of your serializers remain the same)

class LiveClassSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    course = serializers.CharField()
    teacher = 'user.serializer.TeacherProfileSerializer'
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)
    link = serializers.URLField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        teacher_data = instance.get('teacher')
        representation['teacher'] = None  # Initialize as None

        if teacher_data:
            from user.serializer import TeacherProfileSerializer
            if isinstance(teacher_data, dict):
                representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_data)
            elif isinstance(teacher_data, str):
                try:
                    teacher_profile_id = ObjectId(teacher_data)
                    db = get_mongo_db()
                    teacher_profile = db.teacher_profiles.find_one({"_id": teacher_profile_id})
                    if teacher_profile:
                        representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_profile)
                except Exception as e:
                    print(f"Error fetching TeacherProfile with ID '{teacher_data}': {e}")
            elif isinstance(teacher_data, ObjectId):
                db = get_mongo_db()
                teacher_profile = db.teacher_profiles.find_one({"_id": teacher_data})
                if teacher_profile:
                    representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_profile)

         # Handle Course (assuming course ObjectId is stored as string in MongoDB)
        representation['course_id'] = representation.get('course')
        if 'course' in representation:
            del representation['course']

        return representation

    def create(self, validated_data):
        # Insert the live class into the LiveClass collection
        db = get_mongo_db()  # Assume this function gets your MongoDB database
        live_class = {
            'course_id': ObjectId(validated_data['course_id']),
            'teacher_id': ObjectId(validated_data['teacher_id']),
            'start_time': validated_data['start_time'],
            'end_time': validated_data['end_time'],
            'created_at': datetime.now()
        }
        result = db.liveclasss.insert_one(live_class)
        live_class['id'] = str(result.inserted_id)
        return live_class

    def update(self, instance, validated_data):
        # Update the live class in the LiveClass collection
        db = get_mongo_db()
        instance['course_id'] = ObjectId(validated_data.get('course_id', instance['course_id']))
        instance['teacher_id'] = ObjectId(validated_data.get('teacher_id', instance['teacher_id']))
        instance['start_time'] = validated_data.get('start_time', instance['start_time'])
        instance['end_time'] = validated_data.get('end_time', instance['end_time'])
        db.liveclasss.update_one({'_id': ObjectId(instance['id'])}, {'$set': instance})
        return instance


logger = logging.getLogger(__name__)

class AssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True, source='_id.$oid')
    teacher = 'user.serializer.TeacherProfileSerializer'
    course = serializers.CharField()
    title = serializers.CharField(max_length=200)
    total_marks = serializers.IntegerField(default=100)
    description = serializers.CharField()
    due_date = serializers.DateTimeField()
    file = serializers.FileField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if hasattr(instance, '_id'):
            representation['id'] = str(instance._id)
        elif '_id' in instance:
            representation['id'] = str(instance['_id'])

        if '_id' in representation:
            del representation['_id']

        teacher_data = instance.get('teacher')
        representation['teacher'] = None  # Initialize as None

        if teacher_data:
            from user.serializer import TeacherProfileSerializer
            if isinstance(teacher_data, dict):
                representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_data)
            elif isinstance(teacher_data, str):
                try:
                    teacher_profile_id = ObjectId(teacher_data)
                    db = get_mongo_db()
                    teacher_profile = db.teacher_profiles.find_one({"_id": teacher_profile_id})
                    if teacher_profile:
                        representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_profile)
                except Exception as e:
                    print(f"Error fetching TeacherProfile with ID '{teacher_data}': {e}")
            elif isinstance(teacher_data, ObjectId):
                db = get_mongo_db()
                teacher_profile = db.teacher_profiles.find_one({"_id": teacher_data})
                if teacher_profile:
                    representation['teacher'] = TeacherProfileSerializer().to_representation(teacher_profile)

         # Handle Course (assuming course ObjectId is stored as string in MongoDB)
        representation['course_id'] = representation.get('course')
        if 'course' in representation:
            del representation['course']

        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['course'] = ObjectId(validated_data.get('course_id')) # Store Course ObjectId
        try:
            result = db.make_assignments.insert_one(validated_data)
            return db.make_assignments.find_one({"_id": result.inserted_id})
        except Exception as e:
            raise serializers.ValidationError("Error creating assignment in the database.")

    def update(self, instance, validated_data):
        db = get_mongo_db()
        assignment_id = ObjectId(instance['id'])
        validated_data['course'] = ObjectId(validated_data.get('course_id', instance.get('course_id'))) # Store Course ObjectId
        try:
            db.make_assignments.update_one({"_id": assignment_id}, {"$set": validated_data})
            return db.make_assignments.find_one({"_id": assignment_id})
        except Exception as e:
            raise serializers.ValidationError("Error updating assignment in the database.")

class SubmissionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    assignment = AssignmentSerializer()
    user_id = serializers.CharField()
    submission_date = serializers.DateTimeField(read_only=True)
    content = serializers.DictField()
    file = serializers.FileField(allow_null=True, required=False)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'assignment' in instance and isinstance(instance['assignment'], dict):
            instance['assignment'] = AssignmentSerializer().to_representation(instance['assignment'])
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['submission_date'] = datetime.datetime.utcnow()
        result = db.submissions.insert_one(validated_data)
        return db.submissions.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        submission_id = ObjectId(instance['id'])
        db.submissions.update_one({"_id": submission_id}, {"$set": validated_data})
        return db.submissions.find_one({"_id": submission_id})

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


class CourseProgressDetailsSerializer(serializers.Serializer):
    completed = serializers.IntegerField()
    total = serializers.IntegerField()

class CourseProgressResponseSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    details = serializers.DictField(child=CourseProgressDetailsSerializer())

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