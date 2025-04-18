from django.db import models
from django.contrib.auth.models import Group, Permission, AbstractUser
from django.conf import settings

# Create your models here.
class CustomUser(AbstractUser):
    class ROLE(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
    role = models.CharField(max_length=20, choices=ROLE.choices, default=ROLE.STUDENT)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)
    profile = models.ImageField(null=True)
    groups = models.ManyToManyField(Group, related_name="customuser_set", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_user_set", blank=True)
    created_at = models.DateTimeField(auto_now=True)

# class Token(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customuser")
#     key = models.CharField(max_length=40, primary_key=True)
#     created = models.DateTimeField(auto_now_add=True)


    class Meta:
        permissions = [
            ('Assign_teaching_position', 'Can assign teaching position'),
            ('create_course_videos', 'can create course videos'),
            ('create_course_notes', 'can create course notes'),
            ('edit_course_notes', 'can create course notes'),
            ('view_payments', 'can view payments'),
            ('make_payments', 'can make payments'),
            ('make_assignments', 'can make assignments'),
            ('view_assignments', 'can view assignments'),
            ('add_students_to_course', 'can add students to course'),
            ('view_students_in_course', 'can view all students in course'),
            ('edit_students_in_course', 'can edit all students in course'),
            ('view_student_progress', 'view students progress'),
            ('view_attendance_records', 'view attendance'),
            ('send_assignments', 'can send assignments'),
            ('view_course', 'can view all course')

        ]

    def _str__(self):
        return self.username

class TeacherProfile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    role = models.CharField(max_length=20, choices=CustomUser.ROLE.choices, default=CustomUser.ROLE.TEACHER)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    past_experience = models.TextField(null=True)
    course_taken = models.CharField(max_length=100 , null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}"