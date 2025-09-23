from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('conversations/', views.index, name='conversations'),  # Add missing conversations URL
]