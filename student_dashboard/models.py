from django.db import models
from user.models import CustomUser
from courses.models import Course
from payment.models import Payment
# Create your models here.

class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    courses_enrolled = models.ManyToManyField(Course, related_name='enrolled_courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username