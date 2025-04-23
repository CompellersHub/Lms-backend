from django.urls import path
from .import views

urlpatterns = [
    path('category/', views.Category.as_view, name='ctegory'),
    path('blog/', views.Blog.as_view(), name='blog'),
]
