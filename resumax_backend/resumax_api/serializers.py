from rest_framework import serializers
from resumax_algo.models import AttachedFile, ConversationsThread, Conversation

class ConversationsThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationsThread
        fields = ['title', 'user', 'created_at', 'updated_at']
        
class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['prompt', 'response', 'thread']
class AttachedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttachedFile
        fields = ['conversation', 'original_filename', 'stored_filename', 'file_path', 'file_size', 'file_type', 'processing_status', 'error_message']
    
