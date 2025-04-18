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

    # path('pay/<int:order_id>/', views.initiate_paypad_payment, name='paypad_payment'),
    # path('paypad/callback/', views.paypad_callback, name='paypad_callback'),

    path('assignments/', views.Assignment.as_view(), name='assignments'),
    path('assignments/<int:pk>/', views.AssignmentDetail.as_view(), name='assignment_detail'),
    path('assignments/course/', views.AssignmentByCourse.as_view(), name='submission_list'),
    path('submission/', views.AssignmentSubmission.as_view(), name='submission_detail'),
    path('submission/<int:pk>/', views.AssignmentSubmissionDetail.as_view(), name='submission_detail'),
    path('submission/user/', views.AssignmentSubmissionByUser.as_view(), name='submission_by_user'),

    path('modules/', views.Module.as_view(), name='modules'),
    path('modules/<int:pk>/', views.ModuleDetail.as_view(), name='module_detail'),
    path('modules/course/', views.ModuleByCourse.as_view(), name='module_by_course'),

    path('videos/', views.Video.as_view(), name='videos'),
    path('videos/<int:pk>/', views.VideoDetail.as_view(), name='video_detail'),
    path('videos/module/', views.VideoByModule.as_view(), name='video_by_module'),
    

]