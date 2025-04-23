from django.db import models
from user.models import *
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

class Blog(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog_images/')
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
            "teacher": self.teacher.to_dict() if self.teacher else None,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }