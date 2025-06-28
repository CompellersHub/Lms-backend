from django.db import models
from django.conf import settings
from courses.storages_backends import BlogMediaStorage, ProfilePicturesStorage
from user.models import *
from django.contrib.auth.models import AbstractUser, Group, Permission
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
        ('blogger', 'Blogger'),
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        # Add any other roles you might have
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='blogger', # Set 'blogger' as the default role for new BlogUsers
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
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(BlogUser, on_delete=models.CASCADE, default=None, null=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    image = models.FileField(storage=BlogMediaStorage(), blank=True, null=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "image": self.image.url if self.image else None,
            "category": self.category.to_dict(),
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }
    
    