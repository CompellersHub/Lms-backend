from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
# Register your models here.

@admin.register(StudentProfile)
class studentProfileAdmin(ModelAdmin):
    list_display = ['user', 'payment', 'created_at']
    search_fields = ['user', 'payment', 'created_at']
