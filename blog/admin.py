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
    list_display = ['title', 'category', 'created_by', 'created_at']
    list_filter = ['category', 'created_by']
    
@admin.register(BlogUser)
class BlogUserAdmin(ModelAdmin):
    list_display = ['username', 'email', 'phone_number', 'profile_pic']
    search_fields = ['username', 'email']
    list_filter = ['is_staff', 'is_active']