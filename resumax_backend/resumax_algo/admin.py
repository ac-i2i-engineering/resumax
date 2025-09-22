from django.contrib import admin
from .models import AttachedFile, ConversationsThread, Conversation
# Register your models here.
admin.site.register(ConversationsThread)
admin.site.register(Conversation)
admin.site.register(AttachedFile)