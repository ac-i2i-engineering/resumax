from django.db import models
from django.contrib.auth.models import User

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
    prompt = models.TextField(max_length=3000,help_text="The user's prompt",default="")
    response = models.TextField(max_length=3000,help_text="The bot's response",default="")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Conversation {self.id}"

class AttachedFile(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    fileName = models.TextField(max_length=500,help_text="The file path",default="")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.fileName or f"file {self.id}"