from django.urls import path
from .views import *
from blog import views

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<str:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('blogs/', BlogListCreateView.as_view(), name='blog-list-create'),
    path('blogs/<str:pk>/', BlogDetailView.as_view(), name='blog-detail'),
    path('blogusers/', Signup.as_view(), name='bloguser-list-create'),
    # path('blogusers/<str:pk>/', BlogUserDetailView.as_view(), name='bloguser-detail'),
    path('blogusers/login/', Login.as_view(), name='bloguser-login'),
    path('blogusers/logout/', Logout.as_view(), name='bloguser-logout'),
    path('api/upload/image/', BlogImageUploadView.as_view(), name='blog-image-upload'),
    path('webhooks/rankyak/blog-created/', RankYakWebhookView.as_view(), name='rankyak-webhook'),
]
