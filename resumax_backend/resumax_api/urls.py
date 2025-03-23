from django.urls import path
from . import views

urlpatterns = [
    path('threads/', views.get_all_threads, name='thread-list'),
    path('threads/<int:thread_id>/', views.conversations, name='thread-detail'),
    path('threads/<int:thread_id>/delete/', views.delete_thread, name='thread-delete'),
    path('test/', views.test, name='test'),
]