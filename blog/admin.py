from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

# Register your models here.
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display =['name']
    search_fields = ['name']

@admin.register(Blog)
class BlogAdmin(ModelAdmin):
    list_display = ['title', 'category', 'teacher', 'created_at']
    list_filter = ['category', 'teacher']
    