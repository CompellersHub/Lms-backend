from django.db import models
from user.models import CustomUser, TeacherProfile

# Create your models here.
class Category(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=150)
    course_image = models.ImageField(upload_to='course_images/')
    description = models.TextField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.FloatField(default=0)
    instructor = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='instructor_courses', null=True)
    required_materials = models.TextField(blank=True, null=True)
    estimated_time = models.CharField(max_length=100, blank=True, null=True)
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner',
    )

    def __str__(self):
        return self.name
    
class Make_Assignment(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='teacher_assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    upload_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='course_assignments')
    total_marks = models.IntegerField(default=100)
    file = models.FileField(upload_to='assignments/', blank=True)

    def __str__(self):
        return f"{self.title} - {self.course.name}"

class Submission(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='student_submissions')
    assignment = models.ForeignKey('Make_Assignment', on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='submissions/')
    marks_obtained = models.IntegerField(default=0, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='marked_assignments', blank=True, null=True)

class Module(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    order = models.IntegerField(default=0)  # To define the order of modules within a course
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']  # Ensure modules are ordered by the 'order' field

    def __str__(self):
        return f"{self.course.name} - {self.title}"

class Video(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='video_classes', null=True)
    title = models.CharField(max_length=255)
    video_url = models.URLField(null=True, blank=True)  # Store the URL of the video (e.g., YouTube, Vimeo)
    description = models.TextField(blank=True, null=True)
    video_file = models.FileField(upload_to='video_files/', blank=True, null=True)  # Optional: Store the video file
    duration = models.CharField(max_length=50, blank=True, null=True, help_text="Duration of the video (e.g., '15 minutes', '30:45')")
    order = models.IntegerField(default=0, help_text="Order of this video within the module")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Video Classes" # More readable name in the admin

    def __str__(self):
        return f"{self.module.title} - {self.title}"
class CourseOrder(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  
    total_price = models.FloatField(default=0)  
    payment_status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
        default='pending'
    )
    paypad_reference = models.CharField(max_length=100, blank=True, null=True)  # Store Paypad transaction reference
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.payment_status}"

class CourseOrderItem(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    order = models.ForeignKey(CourseOrder, on_delete=models.CASCADE, related_name='order_items')
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    price = models.FloatField(default=0)  # Price of the individual course at the time of order

    def __str__(self):
        return f"{self.course.name} in Order {self.order.id}"
    
