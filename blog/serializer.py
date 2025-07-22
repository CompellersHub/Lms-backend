from datetime import datetime
from django.utils import timezone 
from rest_framework import serializers
from bson.objectid import ObjectId
from blog.models import Blog
from courses.mongo_utils import get_mongo_db
from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
import re
import datetime

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
        validated_data['role'] = 'BLOGGER'  # Set the default role for new BlogUsers
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
    
class ContentBlockSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    type = serializers.ChoiceField(choices=[
        'paragraph', 'heading', 'image', 
        'video', 'quote', 'list', 'button', 'code', 'embed'
    ])
    content = serializers.JSONField()
    style = serializers.ChoiceField(choices=[
        'normal', 'highlight', 'warning', 
        'success', 'info', 'h1', 'h2', 'h3'
    ], required=False)
    anchor = serializers.CharField(required=False)
    link = serializers.URLField(required=False)
    buttonText = serializers.CharField(required=False)
    title = serializers.CharField(required=False)

    def validate_content(self, value):
        """Validate content based on type"""
        block_type = self.initial_data.get('type')
        if block_type == 'list' and not isinstance(value, list):
            raise ValidationError("List blocks must have array content")
        elif block_type != 'list' and not isinstance(value, str):
            raise ValidationError("Non-list blocks must have string content")
        return value

class BlogSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=150)
    slug = serializers.SlugField(max_length=150, required=False)
    author = serializers.SerializerMethodField()
    authorRole = serializers.SerializerMethodField()
    authorImage = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.ListField(child=serializers.CharField())
    image = serializers.SerializerMethodField()
    excerpt = serializers.CharField(max_length=300, required=False)
    content = serializers.ListField(child=serializers.DictField())
    status = serializers.CharField()
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()
    publishedAt = serializers.SerializerMethodField()

    def to_representation(self, instance):
        """Convert MongoDB document to API-friendly format"""
        representation = super().to_representation(instance)
        
        # Handle MongoDB _id field
        if '_id' in instance and isinstance(instance['_id'], ObjectId):
            representation['id'] = str(instance['_id'])
        elif '_id' in representation:
            representation['id'] = str(representation.pop('_id'))
            
        # Convert ObjectId references to strings
        if 'created_by' in representation and isinstance(representation['created_by'], ObjectId):
            representation['created_by'] = str(representation['created_by'])
            
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        
        # Set timestamps
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        
        # Set default status if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'draft'
            
        # Ensure content exists (required field)
        if 'content' not in validated_data:
            validated_data['content'] = []
            
        # Insert into MongoDB
        result = db.blogs.insert_one(validated_data)
        
        # Return the full created document
        return db.blogs.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        blog_id = ObjectId(instance['_id'])
        
        # Update timestamp
        validated_data['updated_at'] = timezone.now()
        
        # Perform the update
        db.blogs.update_one(
            {"_id": blog_id},
            {"$set": validated_data}
        )
        
        # Return the updated document
        return db.blogs.find_one({"_id": blog_id})

    # Keep all your existing get_* methods...
    def get_author(self, obj):
        """Get author username with fallback"""
        created_by = self._get_created_by(obj)
        if isinstance(created_by, ObjectId):
            # You might want to fetch the actual user document here
            return str(created_by)
        elif isinstance(created_by, dict):
            return created_by.get('username', '')
        return ''

    def get_authorRole(self, obj):
        """Get author role with fallback"""
        created_by = self._get_created_by(obj)
        if isinstance(created_by, dict):
            return created_by.get('role', '')
        elif hasattr(created_by, 'role'):
            return created_by.role
        return ''

    def get_authorImage(self, obj):
        """Get author image URL with fallback"""
        created_by = self._get_created_by(obj)
        if not created_by:
            return ''
        
        if isinstance(created_by, dict):
            profile_pic = created_by.get('profile_pic', {})
            if isinstance(profile_pic, dict):
                return profile_pic.get('url', '')
        elif hasattr(created_by, 'profile_pic') and created_by.profile_pic:
            return created_by.profile_pic.url
        return ''

    def get_date(self, obj):
        """Get published date in ISO format"""
        return self._get_iso_date(obj, 'published_at')

    def get_category(self, obj):
        """Handle both string and object/dict categories"""
        category = self._get_category(obj)
        
        if isinstance(category, str):
            return category
        elif isinstance(category, dict):
            return category.get('name', '')
        elif hasattr(category, 'name'):
            return category.name
        return ''

    def get_image(self, obj):
        """Get image URL with proper storage handling"""
        image = obj.get('image') if isinstance(obj, dict) else getattr(obj, 'image', None)
        
        if not image:
            return ''
        
        if isinstance(image, dict):
            return image.get('url', '')
        elif hasattr(image, 'url'):
            return default_storage.url(image.name)
        return str(image)

    def get_createdAt(self, obj):
        """Get creation date in ISO format"""
        return self._get_iso_date(obj, 'created_at')

    def get_updatedAt(self, obj):
        """Get update date in ISO format"""
        return self._get_iso_date(obj, 'updated_at')

    def get_publishedAt(self, obj):
        """Get publication date in ISO format"""
        return self._get_iso_date(obj, 'published_at')

    def _get_created_by(self, obj):
        """Safe getter for created_by field"""
        if isinstance(obj, dict):
            return obj.get('created_by')
        return getattr(obj, 'created_by', None)

    def _get_category(self, obj):
        """Safe getter for category field"""
        if isinstance(obj, dict):
            return obj.get('category')
        return getattr(obj, 'category', None)

    def _get_iso_date(self, obj, field_name):
        """Safe datetime to ISO format conversion"""
        if isinstance(obj, dict):
            dt = obj.get(field_name)
        else:
            dt = getattr(obj, field_name, None)
        
        if isinstance(dt, str):
            try:
                dt = datetime.datetime.fromisoformat(dt)
            except ValueError:
                return None
        
        return dt.isoformat() if dt else None