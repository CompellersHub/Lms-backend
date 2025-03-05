from django.urls import path
from .import views

urlpatterns = [
    path('courses/', views.Courses.as_view(), name='courses'),
    path('courses/<int:pk>/', views.CourseDetail.as_view(), name='course_detail'),
    path('categories/', views.Categories.as_view(), name='categories'),
    path('coursebycategory/<int:pk>/', views.CoursesByCategory.as_view(), name='course_by_category'),]