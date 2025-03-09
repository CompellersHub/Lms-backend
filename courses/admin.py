from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
# Register your models here.

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ['name', 'category', 'price', 'created_by']
    search_fields = ['name', 'category', 'created_by']

@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ['title', 'course', 'created_by']
    search_fields = ['title', 'course', 'created_by']