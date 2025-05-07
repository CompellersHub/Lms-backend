from django.db import models
from django.utils import timezone
from user.models import TeacherProfile  # Ensure these are correctly imported

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
    video_id = models.CharField(null=True, blank=True, max_length=60)
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
            "video_id": self.video_id,
            "description": self.description,
            "duration": self.duration,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class CourseNote(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=255)
    note_file = models.FileField(upload_to='course_notes/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "note_file": self.note_file.url if self.note_file else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Module(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    video = models.ManyToManyField('Video', blank=True, null=True)
    course_note = models.ForeignKey('CourseNote', blank=True, on_delete=models.CASCADE, unique=True, null=True)
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
            "video": [video.to_dict() for video in self.video.all()] if self.video else None,
            "course_note": self.course_note.to_dict() if self.course_note else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Curriculum(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    module = models.ManyToManyField('Module', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "module": [module.to_dict() for module in self.module.all()] if self.module else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class RequiredMaterial(models.Model):
    name1 = models.CharField(max_length=200)
    name2 = models.CharField(max_length=200)
    name3 = models.CharField(max_length=200)
    name4 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.name1}, {self.name2}"

    def to_dict(self):
        return {
            "name1": self.name1,
            "name2": self.name2,
            "name3": self.name3,
            "name4": self.name4,  }
    
class LearningOutcome(models.Model):
    outcome1 = models.CharField(max_length=200)
    outcome2 = models.CharField(max_length=200)
    outcome3 = models.CharField(max_length=200)
    outcome4 = models.CharField(max_length=200,  null=True, blank=True)

    def __str__(self):
        return f"{self.outcome1}, {self.outcome2}"

    def to_dict(self):
        return {
            "outcome1": self.outcome1,
            "outcome2": self.outcome2,
            "outcome3": self.outcome3,
            "outcome4": self.outcome4,
        }
    
class TargetAudience(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    audience1 = models.CharField(max_length=200)
    audience2 = models.CharField(max_length=200)
    audience3 = models.CharField(max_length=200)
    audience4 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.audience1}, {self.audience2}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "audience1": self.audience1,
            "audience2": self.audience2,
            "audience3": self.audience3,
            "audience4": self.audience4,
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
    preview_id = models.CharField(null=True, blank=True, max_length=60)
    preview_description = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.FloatField(default=0)
    instructor = models.ForeignKey('user.TeacherProfile', on_delete=models.CASCADE, related_name='instructor_courses', null=True)
    curriculum = models.ForeignKey('Curriculum', blank=True, null=True, on_delete=models.CASCADE)
    required_materials = models.ForeignKey('RequiredMaterial', on_delete=models.CASCADE, blank=True, null=True)
    learning_outcomes = models.ForeignKey('LearningOutcome', on_delete=models.CASCADE, blank=True, null=True)
    target_audience = models.ForeignKey('TargetAudience', on_delete=models.CASCADE, blank=True, null=True)
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
            "preview_id": self.preview_id,
            "preview_description": self.preview_description,
            "description": self.description,
            "category": self.category.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "price": self.price,
            "learning_outcomes": self.learning_outcomes.to_dict() if self.learning_outcomes else None,
            "target_audience": self.target_audience.to_dict() if self.target_audience else None,
            "curriculum": [module.to_dict() for module in self.curriculum.module.all()] if self.curriculum else None,
            "instructor": self.instructor.to_dict() if self.instructor else None,
            "required_materials": self.required_materials.to_dict() if self.required_materials else None,
            "estimated_time": self.estimated_time,
            "level": self.level,
        }
    

class CourseLibrary(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='course_library')
    file = models.FileField(upload_to='course_library/')
    url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Library for {self.course.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "course": self.course.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Make_Assignment(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey('user.TeacherProfile', on_delete=models.CASCADE, related_name='teacher_assignments')
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



# class CourseOrder(models.Model):
#     id = models.AutoField(primary_key=True, editable=False)
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     total_price = models.FloatField(default=0)
#     payment_status = models.CharField(
#         max_length=20,
#         choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
#         default='pending'
#     )
#     paypad_reference = models.CharField(max_length=100, blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Order {self.id} - {self.payment_status}"

#     def to_dict(self):
#         return {
#             "id": self.id,
#             "user": self.user.to_dict(),
#             "total_price": self.total_price,
#             "payment_status": self.payment_status,
#             "paypad_reference": self.paypad_reference,
#             "created_at": self.created_at.isoformat(),
#             "updated_at": self.updated_at.isoformat(),
#         }

# class CourseOrderItem(models.Model):
#     id = models.AutoField(primary_key=True, editable=False)
#     order = models.ForeignKey(CourseOrder, on_delete=models.CASCADE, related_name='order_items')
#     course = models.ForeignKey('Course', on_delete=models.CASCADE)
#     price = models.FloatField(default=0)

#     def __str__(self):
#         return f"{self.course.name} in Order {self.order.id}"

#     def to_dict(self):
#         return {
#             "id": self.id,
#             "order": self.order.to_dict(),
#             "course": self.course.to_dict(),
#             "price": self.price,
#         }


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


