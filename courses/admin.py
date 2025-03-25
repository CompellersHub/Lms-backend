from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Category, Course, Video, CourseOrder, CourseOrderItem

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ['name', 'category', 'price', 'created_by']
    search_fields = ['name', 'category__name', 'created_by__email']

@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ['title', 'course', 'created_by']
    search_fields = ['title', 'course__name', 'created_by__email']

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
