from django.urls import path
from . import views

urlpatterns = [
    path("threads", views.get_all_threads, name="threads"),
    path("thread/<int:thread_id>", views.get_conversations, name="get_conversations"),
    path("thread/<int:thread_id>/delete", views.delete_thread, name="delete_thread"),
]