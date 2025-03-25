from django.db import models
from user.models import CustomUser

# Create your models here.
class Category(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

    
class Course(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=150)
    course_image = models.ImageField(upload_to='course_images/')
    description = models.TextField()
    student = models.ManyToManyField(CustomUser, related_name='students')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.FloatField(default=0)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    
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
    
class Video(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    title = models.CharField(max_length=150)
    video = models.FileField(upload_to='videos/')
    description = models.TextField()
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.title