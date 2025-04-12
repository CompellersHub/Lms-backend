from rest_framework import serializers
from .models import *


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

    def create(self, validated_data):
        category = Category.objects.create(**validated_data)
        return category
    
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)
        return course
    
class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'

    def create(self, validated_data):
        module = Module.objects.create(**validated_data)
        return module
    
class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = '__all__'

    def create(self, validated_data):
        video = Video.objects.create(**validated_data)
        return video
    
class CourseOrderItemSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source='course.name')

    class Meta:
        model = CourseOrderItem
        fields = ['id', 'order', 'course', 'course_name', 'price']

class CourseOrderSerializer(serializers.ModelSerializer):
    order_items = CourseOrderItemSerializer(many=True, read_only=True, source='order_items')
    
    class Meta:
        model = CourseOrder
        fields = ['id', 'user', 'total_price', 'payment_status', 'created_at', 'updated_at', 'order_items']
        read_only_fields = ['id', 'user', 'total_price', 'payment_status', 'created_at', 'updated_at']