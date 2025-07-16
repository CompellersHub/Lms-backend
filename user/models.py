from bson import ObjectId
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission, AbstractUser
from django.db import models
from django.utils import timezone

from courses.mongo_utils import get_mongo_db
from courses.storages_backends import PublicMediaStorage, ProfilePicturesStorage, TeacherPicturesStorage, SubmissionStorage

from django.utils import timezone
from datetime import timedelta
import random




class OTP(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    purpose = models.CharField(max_length=20, default='SIGNUP')  # Added purpose field with default

    @classmethod
    def generate_otp(cls, email, purpose='SIGNUP'):  # Made purpose optional with default
        """Generate and save a new OTP"""
        # Delete existing OTPs for this email/purpose
        cls.objects.filter(email=email, purpose=purpose).delete()
        
        # Generate 6-digit numeric code
        code = str(random.randint(100000, 999999))
        
        return cls.objects.create(
            email=email,
            code=code,
            purpose=purpose
        )

    def is_expired(self):
        """Check if OTP has expired"""
        expiry_time = self.created_at + timedelta(
            minutes=15  # Fixed expiration to 15 minutes
        )
        return timezone.now() > expiry_time

    def verify(self, entered_code):
        """Verify the OTP code"""
        if not self.is_expired() and self.code == entered_code:
            self.is_verified = True
            self.save()
            return True
        return False



class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db) # Ensure this saves to the correct Django DB alias
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN') # A common practice for superusers

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)
    
    


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.CharField(primary_key=True, max_length=24, unique=True, editable=False, db_column='_id')
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, default='STUDENT')
    course = models.ManyToManyField('courses.Course',  blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_pic = models.FileField(storage=ProfilePicturesStorage(), blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    @classmethod
    def from_mongo(cls, data):
        """
        Create a Django user instance from MongoDB document
        """
        user = cls()
        
        # Map MongoDB fields to Django model fields
        user.id = str(data['_id']) if '_id' in data else None
        user.email = data.get('email', '')
        user.username = data.get('username', '')
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        user.role = data.get('role', 'STUDENT')
        user.phone_number = data.get('phone_number', '')
        user.is_active = data.get('is_active', True)
        user.is_staff = data.get('is_staff', False)
        user.is_superuser = data.get('is_superuser', False)
        user.date_joined = data.get('date_joined', timezone.now())
        
        # Store the raw password if exists (needed for authentication)
        if 'password' in data:
            user.password = data['password']
        
        # Store the complete mongo document for reference
        user._mongo_doc = data
        
        return user

    def save_to_mongo(self):
        """
        Optional: Method to save back to MongoDB if needed
        """
        db = get_mongo_db()
        users_collection = db['customusers']
        
        user_data = {
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'phone_number': self.phone_number,
            'is_active': self.is_active,
            'is_staff': self.is_staff,
            'is_superuser': self.is_superuser,
            'date_joined': self.date_joined,
            'last_login': self.last_login if hasattr(self, 'last_login') else None
        }
        
        if hasattr(self, 'password'):
            user_data['password'] = self.password
        
        if hasattr(self, '_id'):
            users_collection.update_one({'_id': ObjectId(self._id)}, {'$set': user_data})
        else:
            result = users_collection.insert_one(user_data)
            self._id = str(result.inserted_id)
        
        return self

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',  # Unique related_name
        related_query_name='customuser',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',  # Unique related_name
        related_query_name='customuser',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'password']

    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def to_dict(self):
        return {
            "user_id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "password": self.password,
            "course": [course.to_dict() for course in self.course.all()],
            "email": self.email,
            "role": self.role,
            "profile_picture": self.profile_pic.url if self.profile_pic else None,
            "phone_number": self.phone_number,
        }

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True
    
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class TeacherProfile(AbstractUser):
    username = models.CharField(max_length=150, unique=True, default='')
    email = models.EmailField(unique=True, default='')
    password = models.CharField(max_length=128, default='')
    role = models.CharField(max_length=20, default='TEACHER')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.FileField(storage=TeacherPicturesStorage(), blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, default='')
    is_active = models.BooleanField(default=True)
    past_experience = models.TextField(blank=True, null=True)
    course_taken = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "user_id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name":self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "bio": self.bio,
            "password": self.password,
            "profile_picture": self.profile_picture.url if self.profile_picture else None,
            "phone_number": self.phone_number,
            "past_experience": self.past_experience,
            "course_taken": self.course_taken,
            "created_at": self.created_at.isoformat(),
        }
    
    objects = CustomUserManager()

    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

class Submission(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='student_submissions')
    assignment = models.ForeignKey('courses.Make_Assignment', on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(storage=SubmissionStorage(), blank=True, null=True)
    marks_obtained = models.IntegerField(default=0, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey('TeacherProfile', on_delete=models.CASCADE, related_name='marked_assignments', blank=True, null=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student": self.student.to_dict(),
            "assignment": self.assignment.to_dict(),
            "submission_date": self.submission_date.isoformat(),
            "file": self.file.url if self.file else None,
            "marks_obtained": self.marks_obtained,
            "feedback": self.feedback,
            "marked_by": self.marked_by.to_dict() if self.marked_by else None,
        }

class Notification(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.student.user.username}"

    def to_dict(self):
        return {
            "id": self.id,
            "student": self.student.to_dict(),
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
