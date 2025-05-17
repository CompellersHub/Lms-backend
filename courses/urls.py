from django.urls import path
from .import views

urlpatterns = [
    path('courses/', views.Courses.as_view(), name='courses'),
    path('courses/<str:pk>/', views.CourseDetail.as_view(), name='course_detail'),
    path('categories/', views.Categories.as_view(), name='categories'),
    path('coursebycategory/<str:pk>/', views.CoursesByCategory.as_view(), name='course_by_category'),

    # path('orders/', views.CourseOrderAPIView.as_view(), name='course_orders'),
    # path('orders/<str:order_id>/', views.CourseOrderDetailAPIView.as_view(), name='course_order_detail'),
    # path('orders/<str:order_id>/items/', views.CourseOrderItemAPIView.as_view(), name='course_order_items'),

    # path('pay/<int:order_id>/', views.initiate_paypad_payment, name='paypad_payment'),
    # path('paypad/callback/', views.paypad_callback, name='paypad_callback'),

    path('assignments/', views.Assignment.as_view(), name='assignments'),
    path('assignments/<str:pk>/', views.AssignmentDetail.as_view(), name='assignment_detail'),
    path('courses/<str:course_id>/assignments/', views.AssignmentByCourse.as_view(), name='course-assignments'),
    path('submission/', views.AssignmentSubmission.as_view(), name='submission_detail'),
    path('submission/<str:pk>/', views.AssignmentSubmissionDetail.as_view(), name='submission_detail'),
    path('submission/user/<str:pk>/', views.AssignmentSubmissionByUser.as_view(), name='submission_by_user'),

    path('modules/', views.Module.as_view(), name='modules'),
    path('modules/<str:pk>/', views.ModuleDetail.as_view(), name='module_detail'),
    path('modules/course/<str:pk>/', views.ModuleByCourse.as_view(), name='module_by_course'),

    path('videos/', views.Video.as_view(), name='videos'),
    path('videos/<str:pk>/', views.VideoDetail.as_view(), name='video_detail'),
    path('videos/module/<str:pk>/', views.VideoByModule.as_view(), name='video_by_module'),
    path('courselibrary/', views.CourseLibraryView.as_view(), name='courselibrary'),
    path('courselibrary/<str:pk>/', views.CourseLibraryDetailView.as_view(), name='courselibrary_detail'),
    
    path('CreateLiveClass/', views.CreateLiveClassView.as_view(), name='start_live_class'),

    path('courses/payment/initiate/<str:course_id>/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('courses/payment/capture/<str:course_id>/', views.CapturePaymentView.as_view(), name='capture-payment'),
    path('courses/payment/cancel/<str:course_id>/', views.CancelPaymentView.as_view(), name='cancel-payment'),

    path('GenerateCertificate/', views.GenerateCertificatePDF.as_view(), name='generate-certificate'),
    
    
]

