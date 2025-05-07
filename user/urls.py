from django.urls import path
from .import views
from .views import social_callback 

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
    path('student_notifications/<str:customuser_id>/', views.StudentNotificationsView.as_view(), name='student_notifications'),
]