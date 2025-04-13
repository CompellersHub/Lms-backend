from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import *

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ['name', 'level', 'price', 'instructor', 'estimated_time']
    search_fields = ['name', 'category__name', 'instructor__email']

@admin.register(Assignment)
class AssignmentAdmin(ModelAdmin):
    list_display = ['title', 'course', 'teacher', 'due_date']
    search_fields = ['title', 'course__name', 'teacher__email']
    list_filter = ['course', 'teacher']

@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ['student', 'assignment', 'submission_date', 'marks_obtained']
    search_fields = ['student__email', 'assignment__title']
    list_filter = ['student']

@admin.register(Module)
class ModuleAdmin(ModelAdmin):
    list_display = ['title', 'course']
    search_fields = ['title', 'course__name']
    list_filter = ['course']

@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ['title', 'module' ,'duration']
    search_fields = ['title', 'course__name', 'created_by__email']
    list_filter = ['module']

class CourseOrderItemInline(admin.TabularInline):
    model = CourseOrderItem
    extra = 1 

@admin.register(CourseOrder)
class CourseOrderAdmin(ModelAdmin):
    list_display = ['id', 'user', 'total_price', 'payment_status', 'created_at']
    list_filter = ['payment_status', 'created_at']
    search_fields = ['user__email']
    ordering = ['-created_at']
    inlines = [CourseOrderItemInline]  

@admin.register(CourseOrderItem)
class CourseOrderItemAdmin(ModelAdmin):
    list_display = ['id', 'order', 'course', 'price']
    list_filter = ['order']
    search_fields = ['course__name']
