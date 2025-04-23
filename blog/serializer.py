import datetime
from rest_framework import serializers
from bson.objectid import ObjectId
from courses.mongo_utils import get_mongo_db
from user.serializer import TeacherProfileSerializer

class CategorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)

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
        category_id = ObjectId['_id']
        db.categories.update_one({"_id": category_id}, {"$set": validated_data})
        return db.categories.find_one({"_id": category_id})
    

class BlogSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=150)
    description = serializers.CharField()
    category = CategorySerializer()
    teacher = TeacherProfileSerializer()
    image = serializers.URLField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'category' in instance and isinstance(instance['category'], dict):
            instance['category'] = CategorySerializer().to_representation(instance['category'])
        if 'teacher' in instance and isinstance(instance['teacher'], dict):
            instance['teacher'] = TeacherProfileSerializer().to_representation(instance['teacher'])
        return super().to_representation(instance)
    
    def create(self, validated_data):
        db = get_mongo_db()
        result = db.blogs.insert_one(validated_data)
        return db.blogs.find_one({"_id": result.inserted_id})
    
    def update(self, instance, validated_data):
        db = get_mongo_db()
        blog_id = ObjectId['_id']
        db.blogs.update_one({"_id": blog_id}, {"$set": validated_data})
        return db.blogs.find_one({"_id": blog_id})