from django.db import models

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
    