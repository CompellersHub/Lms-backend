import datetime
from rest_framework import serializers
from bson.objectid import ObjectId
from .mongo_utils import get_mongo_db
from user.serializer import TeacherProfileSerializer, CustomUserSerializer

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
    url = serializers.URLField(allow_null=True, required=False)
    duration = serializers.CharField()
    description = serializers.CharField()
    file = serializers.FileField(allow_null=True, required=False)

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
    preview_url = serializers.URLField(allow_blank=True, required=False)
    preview_description = serializers.CharField(max_length=255, allow_blank=True, required=False)
    description = serializers.CharField()
    curriculum = ModuleInCourseSerializer(many=True, required=False) # Use the new serializer and many=True
    category = CategorySerializer()
    price = serializers.FloatField()
    target_audience = TargetAudienceSerializer(required=False)
    learning_outcomes = LearningOutcomeSerializer(required=False)
    students = CustomUserSerializer(many=True, required=False, allow_null=True)
    instructor = TeacherProfileSerializer(allow_null=True, required=False)
    required_materials = RequiredMaterialSerializer(required=False)
    estimated_time = serializers.CharField(allow_blank=True, required=False)
    level = serializers.ChoiceField(choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ])

    def to_representation(self, instance):
        if instance is None:
            return {}
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'category' in instance and isinstance(instance['category'], dict):
            instance['category'] = CategorySerializer().to_representation(instance['category'])
        if 'instructor' in instance and isinstance(instance['instructor'], dict):
            instance['instructor'] = TeacherProfileSerializer().to_representation(instance['instructor'])
        if 'curriculum' in instance and isinstance(instance['curriculum'], list):
            instance['curriculum'] = [ModuleInCourseSerializer().to_representation(item) for item in instance['curriculum']]
        elif 'curriculum' in instance and isinstance(instance['curriculum'], dict):
            instance['curriculum'] = [ModuleInCourseSerializer().to_representation(instance['curriculum'])] # Handle single embedded object?
        if 'students' in instance and isinstance(instance['students'], list):
            instance['students'] = [CustomUserSerializer().to_representation(student) for student in instance['students']]
        if 'target_audience' in instance and isinstance(instance['target_audience'], dict):
            instance['target_audience'] = TargetAudienceSerializer().to_representation(instance['target_audience'])
        if 'learning_outcomes' in instance and isinstance(instance['learning_outcomes'], dict):
            instance['learning_outcomes'] = LearningOutcomeSerializer().to_representation(instance['learning_outcomes'])
        if 'required_materials' in instance and isinstance(instance['required_materials'], dict):
            instance['required_materials'] = RequiredMaterialSerializer().to_representation(instance['required_materials'])
        return super().to_representation(instance)

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

# ... (rest of your serializers remain the same)

class LiveClassSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    course = CourseSerializer()
    teacher = TeacherProfileSerializer()
    description = serializers.CharField()
    date = serializers.DateTimeField()
    duration = serializers.IntegerField()
    link = serializers.URLField()

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'course' in instance and isinstance(instance['course'], dict):
            instance['course'] = CourseSerializer().to_representation(instance['course'])
        if 'teacher' in instance and isinstance(instance['teacher'], dict):
            instance['teacher'] = TeacherProfileSerializer().to_representation(instance['teacher'])
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.live_classes.insert_one(validated_data)
        return db.live_classes.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        live_class_id = ObjectId(instance['id'])
        db.live_classes.update_one({"_id": live_class_id}, {"$set": validated_data})
        return db.live_classes.find_one({"_id": live_class_id})

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

class AssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    course = CourseSerializer()
    title = serializers.CharField(max_length=200)
    total_marks = serializers.IntegerField(default=100)
    description = serializers.DictField()
    due_date = serializers.DateTimeField()
    file = serializers.FileField()

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'course' in instance and isinstance(instance['course'], dict):
            instance['course'] = CourseSerializer().to_representation(instance['course'])
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.assignments.insert_one(validated_data)
        return db.assignments.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        assignment_id = ObjectId(instance['id'])
        db.assignments.update_one({"_id": assignment_id}, {"$set": validated_data})
        return db.assignments.find_one({"_id": assignment_id})

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

class CourseOrderItemSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    order_id = serializers.CharField()
    course_id = serializers.CharField()
    price = serializers.FloatField()
    course_name = serializers.SerializerMethodField()

    def get_course_name(self, instance):
        db = get_mongo_db()
        course = db.courses.find_one({"_id": ObjectId(instance['course_id'])})
        return course.get('name') if course else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_order_items.insert_one(validated_data)
        return db.course_order_items.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        item_id = ObjectId(instance['id'])
        db.course_order_items.update_one({"_id": item_id}, {"$set": validated_data})
        return db.course_order_items.find_one({"_id": item_id})

class CourseOrderSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField()
    total_price = serializers.FloatField(read_only=True)
    payment_status = serializers.CharField(default='pending')
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    order_items = CourseOrderItemSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if '_id' in instance:
            representation['id'] = str(instance['_id'])
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['created_at'] = datetime.datetime.utcnow()
        validated_data['updated_at'] = datetime.datetime.utcnow()
        result = db.course_orders.insert_one(validated_data)
        return db.course_orders.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        validated_data['updated_at'] = datetime.datetime.utcnow()
        order_id = ObjectId(instance['id'])
        db.course_orders.update_one({"_id": order_id}, {"$set": validated_data})
        return db.course_orders.find_one({"_id": order_id})
