from bson import ObjectId
from django.db import models
from django.utils import timezone
from courses.storages_backends import AssignmentStorage, CourseMediaStorage, CourseNotesStorage, VideoMediaStorage
from user.models import TeacherProfile
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=100) # Required

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

class Video(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=255) # Required
    video_id = models.CharField(max_length=60, blank=True, null=True) # REQUIRED
    description = models.TextField(blank=True, null=True    ) # REQUIRED
    video_file = models.FileField(storage=VideoMediaStorage(), blank=True, null=True)
    duration = models.CharField(max_length=50, help_text="Duration of the video (e.g., '15 minutes', '30:45')") # REQUIRED
    order = models.IntegerField(default=1) # REQUIRED, removed default
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

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
            "video_file": self.video_file.url if self.video_file else None,
            "description": self.description,
            "duration": self.duration,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class CourseNote(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=255) # Required
    note_file = models.FileField(storage=CourseNotesStorage(), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

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

class  Course_include(models.Model):
    include = models.TextField()
    include2 = models.TextField()
    include3 = models.TextField()
    include4 = models.TextField()
    include5 = models.TextField()
    include6 = models.TextField()
    include7 = models.TextField()

    def __str__(self):
        return f"{self.include}"

    def to_dict(self):
        return {
            "include": self.include,
            "include2": self.include2,
            "include3": self.include3,
            "include4": self.include4,
            "include5": self.include5,
            "include6": self.include6,
            "include7": self.include7,
        }

class Module(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200) # Required
    video = models.ManyToManyField('Video', blank=True, null=True) # REQUIRED (removed blank=True, null=True)
    course_note = models.ForeignKey('CourseNote', on_delete=models.CASCADE, blank=True, null=True) # Required
    order = models.IntegerField(default=1) # REQUIRED, removed default
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

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
            "course_note": self.course_note ,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Curriculum(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200) # Required
    module = models.ManyToManyField('Module', blank=True, null=True) # REQUIRED (removed blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "module": [module.to_dict() for module in self.module.all()],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

# Represents the RequiredMaterial document in MongoDB
class RequiredMaterial:
    def __init__(self, names: list[str], _id: ObjectId = None):
        self._id = _id
        self.names = names

    def to_dict(self):
        doc = {"names": self.names}
        if self._id:
            doc["_id"] = self._id
        return doc

# Represents the LearningOutcome document in MongoDB
class LearningOutcome:
    def __init__(self, outcomes: list[str], _id: ObjectId = None):
        self._id = _id
        self.outcomes = outcomes

    def to_dict(self):
        doc = {"outcomes": self.outcomes}
        if self._id:
            doc["_id"] = self._id
        return doc

# Represents the TargetAudience document in MongoDB
class TargetAudience:
    def __init__(self, audiences: list[str], _id: ObjectId = None):
        self._id = _id
        self.audiences = audiences

    def to_dict(self):
        doc = {"audiences": self.audiences}
        if self._id:
            doc["_id"] = self._id
        return doc

class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=150) # Required
    course_image = models.FileField(storage=CourseMediaStorage(), blank=True, null=True)
    preview_id = models.FileField(storage=VideoMediaStorage(), blank=True, null=True)
    preview_description = models.CharField(max_length=255, null=True, blank=True) 
    description = models.TextField() # Required
    category = models.ForeignKey('Category', on_delete=models.CASCADE) # Required
    course_include = models.ForeignKey('Course_include', on_delete=models.CASCADE, null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set
    price = models.FloatField() # REQUIRED, removed default
    original_price = models.FloatField(default=1500) # REQUIRED, removed default
    instructor = models.ForeignKey('user.TeacherProfile', on_delete=models.CASCADE) # Required
    curriculum = models.ForeignKey('Curriculum', on_delete=models.CASCADE) # Required
    learning_outcomes = models.JSONField(default=dict, blank=True)
    required_materials = models.JSONField(default=dict, blank=True)
    target_audience = models.JSONField(default=dict, blank=True)
    estimated_time = models.CharField(max_length=100) # Required
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
    ) # REQUIRED, removed default

    def __str__(self):
        return self.name

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "course_image": self.course_image.url,
            "preview_id": self.preview_id.url,
            "preview_description": self.preview_description,
            "description": self.description,
            "category": self.category.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "price": self.price,
            "original_price": self.original_price,
            "course_include": self.course_include.to_dict() if self.course_include else None,
            "curriculum": [module.to_dict() for module in self.curriculum.module.all()],
            "instructor": self.instructor.to_dict(),
            "estimated_time": self.estimated_time,
            "level": self.level,
        }
        if self.learning_outcomes:
            data["learning_outcomes"] = self.learning_outcomes
        if self.required_materials:
            data["required_materials"] = self.required_materials
        if self.target_audience:
            data["target_audience"] = self.target_audience
        return data
        

class CourseLibraryVideo(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200) # Required
    video_file = models.FileField(storage=VideoMediaStorage(), blank=True, null=True) # REQUIRED (removed blank=True, null=True)
    video_id = models.CharField(max_length=50, blank=True, null=True) # REQUIRED (removed blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "video_file": self.video_file.url,
            "video_id": self.video_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class CourseLibrary(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=200) # Required
    courselibraryvideo = models.ManyToManyField('CourseLibraryVideo') # REQUIRED (removed blank=True, null=True)
    course = models.ForeignKey('Course', on_delete=models.CASCADE) # Required
    file = models.FileField(upload_to='course_library/') # REQUIRED (removed blank=True, null=True)
    url = models.URLField() # REQUIRED (removed blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True) # Auto-set
    updated_at = models.DateTimeField(auto_now=True) # Auto-set

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "courselibraryvideo": [video.to_dict() for video in self.courselibraryvideo.all()],
            "course": self.course.to_dict(),
            "file": self.file.url if self.file else None,
            "url": self.url if self.url else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class Make_Assignment(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey('user.TeacherProfile', on_delete=models.CASCADE, related_name='teacher_assignments') # Required
    title = models.CharField(max_length=200) # Required
    description = models.TextField() # Required
    upload_date = models.DateTimeField(auto_now_add=True) # Auto-set
    due_date = models.DateTimeField() # Required
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='course_assignments') # Required
    total_marks = models.IntegerField() # REQUIRED, removed default
    file = models.FileField(storage=AssignmentStorage(), blank=True, null=True)

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

class LiveClass(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE) # Required
    course = models.ForeignKey(Course, on_delete=models.CASCADE) # Required
    title = models.CharField(max_length=255) # Required
    start_time = models.DateTimeField() # Required
    end_time = models.DateTimeField() # Required
    link = models.URLField() # Required
    is_active = models.BooleanField() # REQUIRED, removed default

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
            "is_active": self.is_active,
        }

class CourseEnrollment(models.Model):
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments') # Required
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments') # Required
    enrollment_date = models.DateTimeField(auto_now_add=True) # Auto-set

    class Meta:
        unique_together = ('user_id', 'course_id')

    def __str__(self):
        return f"{self.user_id.email} enrolled in {self.course_id.name}"


class CompletionCertificate(models.Model):
    id = models.AutoField(primary_key=True)
    participant_name = models.CharField(
        _('Participant Name'),
        max_length=255,
        help_text=_('The name of the person receiving the certificate.')
    ) # Required
    course_name = models.CharField(
        _('Course Name'),
        max_length=255,
        help_text=_('The name of the completed course.')
    ) # Required
    completion_date = models.DateField(
        _('Completion Date'),
        help_text=_('The date the course was completed.')
    ) # Required
    signature = models.CharField(
        _('Signature'),
        max_length=255,
        blank=True, null=True, 
        help_text=_('The name or file path of the signature.')
    ) # REQUIRED

    class Meta:
        verbose_name = _('Completion Certificate')
        verbose_name_plural = _('Completion Certificates')

    def __str__(self):
        return f"{self.participant_name} - {self.course_name} - {self.completion_date}"

    def to_dict(self):
        return {
            "id": self.id,
            "participant_name": self.participant_name,
            "course_name": self.course_name,
            "completion_date": self.completion_date.isoformat(),
            "signature": self.signature,
        }