from django.urls import path
from .import views

urlpatterns = [
    path('courses/', views.Courses.as_view(), name='courses'),
    path('courses/<int:pk>/', views.CourseDetail.as_view(), name='course_detail'),
    path('categories/', views.Categories.as_view(), name='categories'),
    path('coursebycategory/<int:pk>/', views.CoursesByCategory.as_view(), name='course_by_category'),

    path('orders/', views.CourseOrderAPIView.as_view(), name='course_orders'),
    path('orders/<int:order_id>/', views.CourseOrderDetailAPIView.as_view(), name='course_order_detail'),
    path('orders/<int:order_id>/items/', views.CourseOrderItemAPIView.as_view(), name='course_order_items'),

    path('pay/<int:order_id>/', views.initiate_paypad_payment, name='paypad_payment'),
    path('paypad/callback/', views.paypad_callback, name='paypad_callback'),
]