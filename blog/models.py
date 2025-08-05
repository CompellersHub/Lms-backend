from bson import ObjectId
from django.db import models
from django.conf import settings
from django.forms import ValidationError
from courses.storages_backends import BlogMediaStorage, ProfilePicturesStorage
from user.models import *
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.text import slugify
# Create your models here.

class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=75)

    def __str__(self):
        return self.name
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
    

class BlogUser(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    profile_pic = models.FileField(storage=ProfilePicturesStorage(), blank=True, null=True)

    ROLE_CHOICES = (
        ('BLOGGER', 'Blogger'),
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        # Add any other roles you might have
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='BLOGGER', # Set 'blogger' as the default role for new BlogUsers
        help_text='The user\'s role in the system.'
    )

    groups = models.ManyToManyField(
        Group,
        related_name='bloguser_set',  # Unique related_name
        related_query_name='bloguser',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='bloguser_set',  # Unique related_name
        related_query_name='bloguser',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    def __str__(self):
        return self.username
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone_number": self.phone_number,
            "profile_pic": self.profile_pic.url if self.profile_pic else None,
            "role": self.role,
        }
    



class Blog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('paragraph', 'Paragraph'),
        ('heading', 'Heading'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('quote', 'Quote'),
        ('list', 'List'),
        ('button', 'Button'),
        ('code', 'Code'),
        ('embed', 'Embed'),
    ]

    IMAGE_CONTENT_SCHEMA = {
        "type": "object",
        "properties": {
            "src": {"type": "string", "format": "uri"},
            "alt": {"type": "string"},
            "caption": {"type": "string"},
            "width": {"type": "number"},
            "height": {"type": "number"}
        },
        "required": ["src", "alt"]
    }

    STYLE_CHOICES = [
        ('normal', 'Normal'),
        ('highlight', 'Highlight'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('info', 'Info'),
        ('h1', 'Heading 1'),
        ('h2', 'Heading 2'),
        ('h3', 'Heading 3'),
    ]

    # Core Fields
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True)  # Legacy content field
    excerpt = models.CharField(max_length=300, blank=True)
    
    # Media
    image = models.FileField(storage=BlogMediaStorage(), blank=True, null=True)
    
    # Relationships
    created_by = models.ForeignKey('BlogUser', on_delete=models.SET_NULL, null=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Content Blocks (stored as JSON)
    content_blocks = models.JSONField(default=list)
    
    # Metadata
    tags = models.JSONField(default=list)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.title
    
    def clean(self):
        """Validate content blocks before saving"""
        super().clean()
        self.validate_content_blocks(self.content_blocks)

    @staticmethod
    def validate_content_blocks(blocks):
        """Validate the structure of content blocks"""
        if not isinstance(blocks, list):
            raise ValidationError("Content blocks must be a list")
        
        for block in blocks:
            if not isinstance(block, dict):
                raise ValidationError("Each block must be a dictionary")
            
            # Required fields
            if 'type' not in block:
                raise ValidationError("Content block missing 'type' field")
            if 'content' not in block:
                raise ValidationError("Content block missing 'content' field")
            
            # Type validation
            if block['type'] not in dict(Blog.CONTENT_TYPE_CHOICES).keys():
                raise ValidationError(f"Invalid content type: {block['type']}")
            
            # Content validation
    
    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            while Blog.objects.filter(slug=self.slug).exclude(_id=self._id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Set published_at if publishing
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
            
        # Auto-create excerpt if empty
        if not self.excerpt:
            self.excerpt = self.description[:300] + '...' if len(self.description) > 300 else self.description
            
        # Convert legacy content to blocks if empty
        if not self.content_blocks and self.description:
            self.content_blocks = [{
                "id": str(ObjectId()),
                "type": "paragraph",
                "content": self.description,
                "style": "normal"
            }]
        
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "author": self.created_by.username if self.created_by else None,
            "authorRole": self.created_by.role if self.created_by else None,
            "authorImage": self.created_by.profile_piczxc5e64.url if self.created_by and hasattr(self.created_by, 'profile_image') else None,
            "date": self.published_at.strftime("%-d %B %Y") if self.published_at else timezone.now().strftime("%-d %B %Y"),
            "category": self.category.name if self.category else None,
            "tags": self.tags,
            "image": self.image.url if self.image.url else None,
            "excerpt": self.excerpt,
            "content": self.content_blocks,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "publishedAt": self.published_at.isoformat() if self.published_at else None
        }

    def add_content_block(self, block_data):
        if not isinstance(block_data, dict):
            raise ValueError("Content block must be a dictionary")
        
        block_data['id'] = str(ObjectId())
        self.content_blocks.append(block_data)
        self.save()
        return block_data

    

    def update_content_block(self, block_id, new_data):
        for block in self.content_blocks:
            if block.get('id') == block_id:
                block.update(new_data)
                self.save()
                return block
        raise ValueError("Content block not found")

    def remove_content_block(self, block_id):
        initial_length = len(self.content_blocks)
        self.content_blocks = [b for b in self.content_blocks if b.get('id') != block_id]
        if len(self.content_blocks) == initial_length:
            raise ValueError("Content block not found")
        self.save()
    