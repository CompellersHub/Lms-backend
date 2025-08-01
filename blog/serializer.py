from datetime import datetime
import uuid
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

from courses.storages_backends import BlogMediaStorage, ProfilePicturesStorage

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
    profile_pic = serializers.FileField(
        required=False, 
        allow_null=True,
        write_only=True  # We'll return URL via profile_pic_url
    )
    profile_pic_url = serializers.SerializerMethodField(read_only=True)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    phone_number = serializers.CharField(max_length=15, allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    role = serializers.CharField(read_only=True)

    def get_profile_pic_url(self, obj):
        if obj.get('profile_pic'):
            return obj['profile_pic']
        return None

    def validate_username(self, value):
        db = get_mongo_db()
        if db.bloguser.find_one({"username": value}):
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        db = get_mongo_db()
        if db.bloguser.find_one({"email": value}):
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_profile_pic(self, value):
        if value:
            # File size validation (5MB max)
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise ValidationError(f'Max file size is {max_size/1024/1024}MB')
            
            # File type validation
            valid_types = ['image/jpeg', 'image/png', 'image/webp']
            if value.content_type not in valid_types:
                raise ValidationError('Only JPEG, PNG, and WebP images are allowed')
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        if '_id' in instance and isinstance(instance['_id'], ObjectId):
            representation['id'] = str(instance['_id'])
        elif '_id' in representation:
            representation['id'] = str(representation['_id'])
            
        if '_id' in representation:
            del representation['_id']
        if 'password' in representation:
            del representation['password']
            
        return representation

    def create(self, validated_data):
        db = get_mongo_db()
        profile_pic = validated_data.pop('profile_pic', None)
        
        if profile_pic:
            try:
                storage = ProfilePicturesStorage()
                ext = profile_pic.name.split('.')[-1].lower()
                filename = f"user_{uuid.uuid4()}.{ext}"
                saved_name = storage.save(filename, profile_pic)
                validated_data['profile_pic'] = storage.url(saved_name)
            except Exception as e:
                raise serializers.ValidationError(f"Profile picture upload failed: {str(e)}")

        validated_data.update({
            'password': make_password(validated_data['password']),
            'created_at': timezone.now(),
            'role': 'BLOGGER',
            '_id': ObjectId()  # Generate new ObjectId
        })

        try:
            result = db.bloguser.insert_one(validated_data)
            return db.bloguser.find_one({"_id": result.inserted_id})
        except Exception as e:
            if 'profile_pic' in validated_data:
                storage.delete(filename)
            raise serializers.ValidationError(f"Database error: {str(e)}")

    def update(self, instance, validated_data):
        db = get_mongo_db()
        user_id = ObjectId(instance['id'])
        old_profile_pic = instance.get('profile_pic')
        new_profile_pic = validated_data.pop('profile_pic', None)
        
        if new_profile_pic:
            storage = ProfilePicturesStorage()
            
            # Delete old picture if exists
            if old_profile_pic:
                try:
                    old_filename = old_profile_pic.split('/')[-1]
                    storage.delete(old_filename)
                except Exception:
                    pass  # Log this error in production
            
            # Upload new picture
            ext = new_profile_pic.name.split('.')[-1].lower()
            filename = f"user_{uuid.uuid4()}.{ext}"
            saved_name = storage.save(filename, new_profile_pic)
            validated_data['profile_pic'] = storage.url(saved_name)
        
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        
        db.bloguser.update_one({"_id": user_id}, {"$set": validated_data})
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
    author = serializers.CharField(default="Titans Careers Editorial Team")
    authorRole = serializers.CharField(default="AML/KYC Compliance Experts")
    authorImage = serializers.URLField(default="https://titanscareers.s3.amazonaws.com/profile_pictures/user_e9a513d2-1e98-48e8-9780-3b3693fc042e.png")
    date = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.ListField(child=serializers.CharField())
    image = serializers.FileField(
        required=False,
        allow_null=True,
        write_only=True,
        
    )
    image_url = serializers.SerializerMethodField(read_only=True)
    excerpt = serializers.CharField(max_length=300, required=False)
    content = serializers.ListField(
    child=serializers.DictField(),
    required=False,
    default=list  # Ensure empty list if not provided
    )
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
            
        return representation

    

    def get_image_url(self, obj):
        if 'image' in obj and obj['image']:
            if isinstance(obj['image'], str):
                return obj['image']
            return BlogMediaStorage().url(obj['image'])
        return None

    def get_date(self, obj):
        if 'publishedAt' in obj:
            return obj['publishedAt'].strftime("%B %d, %Y")
        return timezone.now().strftime("%B %d, %Y")

    def validate_image(self, value):
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError(f"Image size cannot exceed {max_size/1024/1024}MB")
        return value


    def create(self, validated_data):
        db = get_mongo_db()
        
        
        # Handle image upload
        if 'image' in validated_data:
            storage = BlogMediaStorage()
            ext = validated_data['image'].name.split('.')[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            saved_name = storage.save(filename, validated_data['image'])
            validated_data['image'] = storage.url(saved_name)

        # Set timestamps
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        
        # Set default status if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'draft'
            
        # Ensure content exists
        if 'content' not in validated_data:
            validated_data['content'] = []
            
        # Insert into MongoDB
        result = db.blogs.insert_one(validated_data)
        return db.blogs.find_one({"_id": result.inserted_id})

    def update(self, instance, validated_data):
        db = get_mongo_db()
        blog_id = ObjectId(instance['_id'])
        new_image = validated_data.pop('image', None)
        
        # Handle image update
        if new_image:
            storage = BlogMediaStorage()
            
            # Delete old image if exists
            old_image = instance.get('image')
            if old_image and isinstance(old_image, str):
                try:
                    old_filename = old_image.split('/')[-1]  # Extract filename from URL
                    storage.delete(old_filename)
                except Exception:
                    pass  # Log this error in production
            
            # Upload new image
            try:
                ext = new_image.name.split('.')[-1].lower()
                filename = f"{uuid.uuid4()}.{ext}"
                saved_name = storage.save(filename, new_image)
                validated_data['image'] = storage.url(saved_name)
            except Exception as e:
                raise serializers.ValidationError(f"Image upload failed: {str(e)}")

        # Update timestamp
        validated_data['updated_at'] = timezone.now()
        
        # Perform the update
        db.blogs.update_one(
            {"_id": blog_id},
            {"$set": validated_data}
        )
        
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


class BlogImageUploadSerializer(serializers.Serializer):
    image = serializers.FileField(
        
        max_length=100,
        allow_empty_file=False
    )

    def validate_image(self, value):
        # File size validation (5MB max)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise ValidationError(f'Max image size is {max_size/1024/1024}MB')
        
        # File type validation
        valid_types = ['image/jpeg', 'image/png', 'image/webp']
        if value.content_type not in valid_types:
            raise ValidationError('Only JPEG, PNG, and WebP images are allowed')
        
        return value

    def create(self, validated_data):
        storage = BlogMediaStorage()
        image_file = validated_data['image']
        
        # Generate unique filename
        ext = image_file.name.split('.')[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Save to S3
        saved_name = storage.save(filename, image_file)
        
        return {
            'url': storage.url(saved_name),
            'filename': filename
        }