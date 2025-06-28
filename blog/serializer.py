from datetime import datetime
from rest_framework import serializers
from bson.objectid import ObjectId
from courses.mongo_utils import get_mongo_db
from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
import re

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
        category_id = ObjectId(instance['_id'])
        db.categories.update_one({"_id": category_id}, {"$set": validated_data})
        return db.categories.find_one({"_id": category_id})
    
def check_password(password):
    password_pattern = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    match = re.match(password_pattern, string=password)
    return bool(match)

def validate_password(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not check_password(password):
        raise ValidationError("Password must contain at least one uppercase, one lowercase, one digit and one special character")

class BlogUserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    phone_number = serializers.CharField(max_length=15, allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    
    # Add the 'role' field. It should be read-only if it's set internally upon creation.
    role = serializers.CharField(read_only=True) 

    def validate_username(self, value):
        db = get_mongo_db()
        # Query the MongoDB 'bloguser' collection for uniqueness
        if db.bloguser.find_one({"username": value}):
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        db = get_mongo_db()
        # Query the MongoDB 'bloguser' collection for uniqueness
        if db.bloguser.find_one({"email": value}):
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def to_representation(self, instance):
        # Create a mutable copy to modify, as 'instance' might be an immutable MongoDB result
        representation = super().to_representation(instance)
        
        # Convert MongoDB's _id to 'id' string for the response
        if '_id' in instance and isinstance(instance['_id'], ObjectId):
            representation['id'] = str(instance['_id'])
        elif '_id' in representation: # In case super().to_representation already included _id
            representation['id'] = str(representation['_id'])
            
        # Ensure '_id' is removed from the final representation if 'id' is preferred
        if '_id' in representation:
            del representation['_id']
            
        # Ensure password is never included in the response
        if 'password' in representation:
            del representation['password']
            
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        
        # Hash the password before saving
        validated_data['password'] = make_password(validated_data['password'])
        
        # Set creation timestamp
        validated_data['created_at'] = datetime.now() # Using local time, consider .utcnow() if server is UTC
        
        # --- IMPORTANT CHANGE: Set the role to 'blogger' ---
        validated_data['role'] = 'blogger' 
        # --- End of IMPORTANT CHANGE ---

        result = db.bloguser.insert_one(validated_data)
        
        # Fetch the newly created document from MongoDB to return a complete representation
        return db.bloguser.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        
        # Get the user's MongoDB _id from the instance's 'id' field (which holds the string representation)
        user_id = ObjectId(instance['id'])
        
        # Re-hash password if it's being updated
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        
        # --- IMPORTANT FIX: Corrected collection name from 'blogusers' to 'bloguser' ---
        db.bloguser.update_one({"_id": user_id}, {"$set": validated_data})
        # --- End of IMPORTANT FIX ---
        
        # Fetch the updated document from MongoDB to return a complete representation
        return db.bloguser.find_one({"_id": user_id})
    
class BlogSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=150)
    description = serializers.CharField()
    category = CategorySerializer()
    created_by = BlogUserSerializer()
    image = serializers.URLField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if '_id' in instance:
            instance['id'] = str(instance['_id'])
            del instance['_id']
        if 'category' in instance and isinstance(instance['category'], dict):
            instance['category'] = CategorySerializer().to_representation(instance['category'])
        if 'created_by' in instance and isinstance(instance['created_by'], dict):
            instance['created_by'] = BlogUserSerializer().to_representation(instance['created_by'])
        return super().to_representation(instance)

    def create(self, validated_data):
        db = get_mongo_db()
        category_data = validated_data.pop('category')
        category_serializer = CategorySerializer(data=category_data)
        if category_serializer.is_valid():
            category_instance = category_serializer.save()
            validated_data['category'] = category_instance
        else:
            raise serializers.ValidationError("Invalid category data")

        validated_data['created_at'] = datetime.datetime.now()
        result = db.blogs.insert_one(validated_data)
        return db.blogs.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        blog_id = ObjectId(instance['_id'])

        if 'category' in validated_data:
            category_data = validated_data.pop('category')
            category_serializer = CategorySerializer(data=category_data)
            if category_serializer.is_valid():
                category_instance = category_serializer.save()
                validated_data['category'] = category_instance
            else:
                raise serializers.ValidationError("Invalid category data")

        db.blogs.update_one({"_id": blog_id}, {"$set": validated_data})
        return db.blogs.find_one({"_id": blog_id})
