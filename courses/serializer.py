import datetime
from rest_framework import serializers
from .mongo_utils import get_mongo_db
from bson.objectid import ObjectId

class CategorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    # Assuming your Category documents in MongoDB have a 'description' field
    description = serializers.CharField(allow_blank=True, required=False)

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.categories.insert_one(validated_data)
        return db.categories.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        category_id = instance['_id']
        db.categories.update_one({"_id": category_id}, {"$set": validated_data})
        return db.categories.find_one({"_id": category_id})


class CourseSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    # Assuming your Course documents have 'category_id' (referencing a Category document)
    category_id = serializers.CharField()
    description = serializers.DictField()
    price = serializers.FloatField()
    # Add other fields based on your Course document structure

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.courses.insert_one(validated_data)
        return db.courses.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        course_id = instance['_id']
        db.courses.update_one({"_id": course_id}, {"$set": validated_data})
        return db.courses.find_one({"_id": course_id})


class ModuleSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    course_id = serializers.CharField() # Assuming a reference to a Course
    title = serializers.CharField(max_length=200)
    order = serializers.IntegerField()
    # Add other fields based on your Module document structure

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.modules.insert_one(validated_data)
        return db.modules.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        module_id = instance['_id']
        db.modules.update_one({"_id": module_id}, {"$set": validated_data})
        return db.modules.find_one({"_id": module_id})


class AssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    module_id = serializers.CharField() # Assuming a reference to a Module
    title = serializers.CharField(max_length=200)
    description = serializers.DictField()
    due_date = serializers.DateTimeField()
    # Add other fields

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.assignments.insert_one(validated_data)
        return db.assignments.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        assignment_id = instance['_id']
        db.assignments.update_one({"_id": assignment_id}, {"$set": validated_data})
        return db.assignments.find_one({"_id": assignment_id})


class SubmissionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    assignment_id = serializers.CharField() # Assuming a reference to an Assignment
    user_id = serializers.CharField() # Assuming you store user IDs
    submission_date = serializers.DateTimeField(read_only=True)
    # Add fields for the actual submission content (e.g., text, file path)
    content = serializers.DictField() # Assuming a dictionary for submission content
    file = serializers.FileField(allow_null=True, required=False) # Optional file upload

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['submission_date'] = datetime.utcnow() # Set submission date on creation
        result = db.submissions.insert_one(validated_data)
        return db.submissions.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        submission_id = instance['_id']
        db.submissions.update_one({"_id": submission_id}, {"$set": validated_data})
        return db.submissions.find_one({"_id": submission_id})


class VideoSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    module_id = serializers.CharField() # Assuming a reference to a Module
    title = serializers.CharField(max_length=200)
    url = serializers.URLField(allow_null=True, required=False) # Optional URL for video
    duration = serializers.FloatField()
    description = serializers.DictField(allow_null=True, required=False)
    file = serializers.FileField(allow_null=True, required=False) # Optional file upload
    # Add other fields

    def to_representation(self, instance):
        instance['id'] = str(instance['_id'])
        del instance['_id']
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.videos.insert_one(validated_data)
        return db.videos.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        video_id = instance['_id']
        db.videos.update_one({"_id": video_id}, {"$set": validated_data})
        return db.videos.find_one({"_id": video_id})


class CourseOrderItemSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    order_id = serializers.CharField() # Assuming a reference to CourseOrder
    course_id = serializers.CharField() # Assuming a reference to Course
    price = serializers.FloatField()
    course_name = serializers.SerializerMethodField() # To fetch course name

    def get_course_name(self, instance):
        db = get_mongo_db()
        course = db.courses.find_one({"_id": ObjectId(instance['course_id'])})
        return course.get('name') if course else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = str(instance['_id'])
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        result = db.course_order_items.insert_one(validated_data)
        return db.course_order_items.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        item_id = instance['_id']
        db.course_order_items.update_one({"_id": item_id}, {"$set": validated_data})
        return db.course_order_items.find_one({"_id": item_id})


class CourseOrderSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField() # Assuming you store user IDs
    total_price = serializers.FloatField(read_only=True)
    payment_status = serializers.CharField(default='pending')
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    order_items = CourseOrderItemSerializer(many=True, read_only=True) # Consider how to handle creation

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = str(instance['_id'])
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        validated_data['created_at'] = datetime.utcnow()
        validated_data['updated_at'] = datetime.utcnow()
        result = db.course_orders.insert_one(validated_data)
        return db.course_orders.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        validated_data['updated_at'] = datetime.utcnow()
        order_id = instance['_id']
        db.course_orders.update_one({"_id": order_id}, {"$set": validated_data})
        return db.course_orders.find_one({"_id": order_id})