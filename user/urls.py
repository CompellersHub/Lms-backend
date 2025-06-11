from django.urls import path
from .import views
from .views import social_callback 
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('signup/', views.Signup.as_view(), name='signup'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('csrftoken/', views.GetCSRFToken.as_view(), name='csrf_token'),
    path("callback/", social_callback, name="social_callback"),
    path("student/", views.Student.as_view(), name='student'),
    path("student/<str:pk>/", views.StudentDetail.as_view(), name='student_detail'),
    path("teacher/", views.Teacher.as_view(), name='teacher'),
    path('api/google-login/', views.GoogleLoginView.as_view(), name='google-login'),
    path('students/filter/<str:course_id>', views.StudentFilterByCourse.as_view(), name='student-filter-by-course'), # New URL
     path('teacher-login/', views.TeacherLoginView.as_view(), name='teacher_login'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'), # For refreshing tokens
    # path('users/<str:user_id>/courses/<str:course_id>/progress/', views.UserCourseProgressView.as_view(), name='user-course-progress'),
    path('users/<str:user_id>/courses/<str:course_id>/progress/details/', views.CourseProgressDetailView.as_view(), name='course-progress-details'),
    # ... other course URLs
]