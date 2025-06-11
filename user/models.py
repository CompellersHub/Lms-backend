from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission, AbstractUser
from django.db import models
from django.utils import timezone



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
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

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
    profile_picture = models.ImageField(upload_to='teacher_pics/', blank=True, null=True)
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

class Submission(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='student_submissions')
    assignment = models.ForeignKey('courses.Make_Assignment', on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='submissions/')
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
