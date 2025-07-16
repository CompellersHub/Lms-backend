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
    path('teachers/signup/', views.TeacherSignupView.as_view(), name='teacher-signup'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'), # For refreshing tokens
    # path('users/<str:user_id>/courses/<str:course_id>/progress/', views.UserCourseProgressView.as_view(), name='user-course-progress'),
    path('user-course-progress/<str:user_id>/<str:course_id>/', views.UserCourseProgressView.as_view(), name='user_course_progress'),
    # ... other course URLs
    path('profile/', views.GetCurrentUserProfile.as_view(), name='get_current_user_profile'),
    path('teacher/course-progress/<str:course_id>/', views.TeacherCourseProgressListView.as_view(), name='teacher_course_progress_list'),
    path('send-template-1/', views.SendTemplate1View.as_view(), name='send-template-1'),

    path('teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher-dashboard'),
    path('test-otp/', views.TestEmailView.as_view(), name='test-otp'),
]