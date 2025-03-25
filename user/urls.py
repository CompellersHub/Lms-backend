from django.urls import path
from .import views
from .views import social_callback 

urlpatterns = [
    path('signup/', views.Signup.as_view(), name='signup'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('csrftoken/', views.Get_csrf_token.as_view(), name='csrf_token'),
    path("callback/", social_callback, name="social_callback"),
]