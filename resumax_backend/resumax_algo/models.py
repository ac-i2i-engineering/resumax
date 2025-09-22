from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
import os

class Document(models.Model):
    '''
    Document model to store text content in the vector database for retrieval.
    
    This model provides the structure for storing documents that will be embedded
    in a vector database for RAG (Retrieval Augmented Generation) operations.

    To use this model:
    1. Create document instances:
        doc = Document.objects.create(
            title="Sample Document",
            content="Your document content here"
        )

    2. Load into vector database:
        from langchain.vectorstores import FAISS
        from langchain.embeddings import OpenAIEmbeddings
        
        # Get all documents
        documents = Document.objects.all()
        
        # Create text/metadata pairs
        texts = [doc.get_vectordb_text() for doc in documents]
        
        # Initialize vector store
        vectorstore = FAISS.from_texts(
            texts,
            OpenAIEmbeddings()
        )

    3. Query the vector store:
        results = vectorstore.similarity_search("your query here")
    '''
    content = models.TextField(help_text="The main text content to be vectorized")
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_vectordb_text(self):
        """Return text to be vectorized"""
        return f"{self.title} {self.content}"

    def __str__(self):
        return self.title or f"Document {self.id}"
    
class ConversationsThread(models.Model):
    '''
    ChatThread model to store chat messages in the database for retrieval.
    '''
    title = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"ChatThread {self.id}"

class Conversation(models.Model):
    '''
    Chat model to store chat messages in the database for retrieval.
    '''
    thread = models.ForeignKey(ConversationsThread, on_delete=models.CASCADE)
    prompt = models.TextField(max_length=8000,help_text="The user's prompt",default="")
    response = models.TextField(max_length=20000,help_text="The bot's response",default="")
    internal_analysis = models.TextField(help_text="Internal analysis for the conversation",default="")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Conversation {self.id}"

class AttachedFile(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255, help_text="Original file name", default="")
    stored_filename = models.CharField(max_length=255, help_text="Stored file name", default="")
    file_path = models.CharField(max_length=500, help_text="File path", default="")
    file_size = models.BigIntegerField(help_text="File size in bytes", default=0)
    file_type = models.CharField(max_length=100, help_text="File type/MIME type", default="")
    processing_status = models.CharField(max_length=20, help_text="Processing status", default="pending")
    error_message = models.TextField(help_text="Error message if any", default="")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.original_filename or f"file {self.id}"
    
    def get_full_file_path(self):
        """Get the full filesystem path to the file"""
        if self.stored_filename:
            from django.conf import settings
            import pathlib
            return pathlib.Path(settings.MEDIA_ROOT) / self.stored_filename
        return None

# Signal handlers for automatic file deletion
@receiver(post_delete, sender=AttachedFile)
def delete_file_on_model_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem when corresponding `AttachedFile` object is deleted.
    """
    file_path = instance.get_full_file_path()
    if file_path and file_path.exists():
        try:
            file_path.unlink()
            print(f"Successfully deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
    elif file_path:
        print(f"File not found for deletion: {file_path}")

@receiver(pre_save, sender=AttachedFile)
def delete_file_on_change(sender, instance, **kwargs):
    """
    Deletes old file from filesystem when corresponding `AttachedFile` object is updated
    with new file.
    """
    if not instance.pk:
        return False

    try:
        old_instance = AttachedFile.objects.get(pk=instance.pk)
        old_file_path = old_instance.get_full_file_path()
        new_file_path = instance.get_full_file_path()
        
        if old_file_path != new_file_path and old_file_path and old_file_path.exists():
            old_file_path.unlink()
    except AttachedFile.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error deleting old file: {e}")