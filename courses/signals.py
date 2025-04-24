from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LiveClass, Notification

@receiver(post_save, sender=LiveClass)
def notify_students(sender, instance, **kwargs):
    if instance.is_active:
        students = instance.course.students.all()
        for student in students:
            Notification.objects.create(
                student=student,
                message=f"A new live class '{instance.title}' for the course '{instance.course.name}' has started by {instance.teacher.user.username}."
            )
