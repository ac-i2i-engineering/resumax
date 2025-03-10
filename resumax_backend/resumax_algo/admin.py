from django.contrib import admin
from .models import AttachedFile, Document, ConversationsThread, Conversation
# Register your models here.
admin.site.register(Document)
admin.site.register(ConversationsThread)
admin.site.register(Conversation)
admin.site.register(AttachedFile)