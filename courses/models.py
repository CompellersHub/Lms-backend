from django.db import models
from django.utils import timezone
from user.models import CustomUser, TeacherProfile  # Ensure these are correctly imported

class Category(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

class Video(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=255)
    video_url = models.URLField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    video_file = models.FileField(upload_to='video_files/', blank=True, null=True)
    duration = models.CharField(max_length=50, blank=True, null=True, help_text="Duration of the video (e.g., '15 minutes', '30:45')")
    order = models.IntegerField(default=0, help_text="Order of this video within the module")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Video Classes"

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "video_url": self.video_url,
            "description": self.description,
            "video_file": self.video_file.url if self.video_file else None,
            "duration": self.duration,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Module(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    video = models.ManyToManyField('Video', related_name='module_videos', blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "order": self.order,
            "video": [video.to_dict() for video in self.video.all()],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

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
    student = models.ManyToManyField(CustomUser, related_name='student_courses', blank=True)
    price = models.FloatField(default=0)
    instructor = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='instructor_courses', null=True)
    module = models.ManyToManyField(Module, related_name='course_modules', blank=True)
    required_materials = models.TextField(blank=True, null=True)
    learning_outcomes = models.TextField(blank=True, null=True)
    target_audience = models.TextField(blank=True, null=True)
    estimated_time = models.CharField(max_length=100, blank=True, null=True)
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner',
    )

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "course_image": self.course_image.url if self.course_image else None,
            "description": self.description,
            "category": self.category.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "price": self.price,
            "student": [student.to_dict() for student in self.student.all()],
            "learning_outcomes": self.learning_outcomes,
            "target_audience": self.target_audience,
            "module": [module.to_dict() for module in self.module.all()],
            "instructor": self.instructor.to_dict() if self.instructor else None,
            "required_materials": self.required_materials,
            "estimated_time": self.estimated_time,
            "level": self.level,
        }

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

    def to_dict(self):
        return {
            "id": self.id,
            "teacher": self.teacher.to_dict(),
            "title": self.title,
            "description": self.description,
            "upload_date": self.upload_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "course": self.course.to_dict(),
            "total_marks": self.total_marks,
            "file": self.file.url if self.file else None,
        }

class Submission(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='student_submissions')
    assignment = models.ForeignKey('Make_Assignment', on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_date = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='submissions/')
    marks_obtained = models.IntegerField(default=0, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='marked_assignments', blank=True, null=True)

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

class CourseOrder(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    total_price = models.FloatField(default=0)
    payment_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
        default='pending'
    )
    paypad_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.payment_status}"

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict(),
            "total_price": self.total_price,
            "payment_status": self.payment_status,
            "paypad_reference": self.paypad_reference,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class CourseOrderItem(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    order = models.ForeignKey(CourseOrder, on_delete=models.CASCADE, related_name='order_items')
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    price = models.FloatField(default=0)

    def __str__(self):
        return f"{self.course.name} in Order {self.order.id}"

    def to_dict(self):
        return {
            "id": self.id,
            "order": self.order.to_dict(),
            "course": self.course.to_dict(),
            "price": self.price,
        }


class LiveClass(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    link = models.URLField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.course.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "teacher": self.teacher.to_dict(),
            "course": self.course.to_dict(),
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "link": self.link,
            
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
