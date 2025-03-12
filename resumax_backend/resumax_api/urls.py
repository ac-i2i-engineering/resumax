from django.urls import path
from . import views

urlpatterns = [
    path("threads", views.threads, name="threads"),
    path("thread/<int:thread_id>", views.get_conversations, name="get_conversations"),
]