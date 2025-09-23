"""
Simplified test cases for conversation history functionality.

This module focuses on testing the core conversation history logic
without complex database operations.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from django.contrib.auth.models import User

from resumax_algo.models import ConversationsThread, Conversation
from resumax_algo.gemini_model import generate_response, _get_conversation_history


@pytest.fixture
def test_user(django_user_model):
    """Create a test user for conversation tests."""
    return django_user_model.objects.create_user(
        username='testuser',
        email='test@example.com'
    )


@pytest.fixture
def mock_genai():
    """Mock the Google GenAI client for testing."""
    with patch('resumax_algo.gemini_model.genai.Client') as mock_client_class:
        # Mock the client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock the chat creation
        mock_chat = MagicMock()
        mock_chat.send_message = AsyncMock()
        mock_chat.send_message.return_value.text = "Mocked AI response"
        
        mock_client.chats.create = AsyncMock(return_value=mock_chat)
        mock_client.files.upload = MagicMock()
        mock_client.files.upload.return_value.uri = "https://generativelanguage.googleapis.com/v1beta/files/test123"
        
        yield mock_client


class TestBasicConversationHistory:
    """Basic test cases for conversation history functionality."""

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_get_conversation_history_empty_thread(self, test_user):
        """Test getting history from an empty thread."""
        # Create a thread with no conversations
        thread = ConversationsThread.objects.create(
            title="Empty Thread",
            user=test_user
        )
        
        history = await _get_conversation_history(thread.id)
        assert history == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_get_conversation_history_nonexistent_thread(self):
        """Test getting history from a non-existent thread."""
        history = await _get_conversation_history(99999)
        assert history == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_generate_response_empty_prompt(self):
        """Test generating response with empty prompt raises exception."""
        with pytest.raises(Exception, match="Prompt text cannot be empty"):
            await generate_response("")
        
        with pytest.raises(Exception, match="Prompt text cannot be empty"):
            await generate_response("   ")  # Whitespace only

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_generate_response_new_conversation(self, mock_genai):
        """Test generating response for a new conversation (no thread_id)."""
        response = await generate_response("Hello, I'm a new user")
        
        assert response == "Mocked AI response"
        mock_genai.chats.create.assert_called_once()
        
        # Verify minimal history was passed (empty or minimal)
        call_args = mock_genai.chats.create.call_args
        history = call_args.kwargs.get('history', [])
        assert isinstance(history, list)

    @pytest.mark.django_db
    @pytest.mark.asyncio 
    async def test_conversation_history_structure(self, test_user):
        """Test the structure of conversation history."""
        # Create thread and conversation manually
        thread = ConversationsThread.objects.create(
            title="Test Thread",
            user=test_user
        )
        
        Conversation.objects.create(
            thread=thread,
            prompt="Hello",
            response="Hi there!"
        )
        
        history = await _get_conversation_history(thread.id)
        
        assert len(history) == 2  # user + model messages
        
        # Check user message structure
        user_msg = history[0]
        assert user_msg['role'] == 'user'
        assert 'parts' in user_msg
        assert user_msg['parts'][0]['text'] == "Hello"
        
        # Check model message structure
        model_msg = history[1]
        assert model_msg['role'] == 'model'
        assert 'parts' in model_msg
        assert model_msg['parts'][0]['text'] == "Hi there!"


class TestConversationPersistence:
    """Test cases for conversation data persistence."""

    @pytest.mark.django_db
    def test_conversation_creation(self, test_user):
        """Test that conversations can be created and saved."""
        thread = ConversationsThread.objects.create(
            title="Test Thread",
            user=test_user
        )
        
        conversation = Conversation.objects.create(
            thread=thread,
            prompt="Test prompt",
            response="Test response"
        )
        
        assert conversation.prompt == "Test prompt"
        assert conversation.response == "Test response"
        assert conversation.thread == thread
        assert conversation.created_at is not None

    @pytest.mark.django_db
    def test_thread_conversation_relationship(self, test_user):
        """Test the relationship between threads and conversations."""
        thread = ConversationsThread.objects.create(
            title="Test Thread",
            user=test_user
        )
        
        # Create multiple conversations
        conv1 = Conversation.objects.create(
            thread=thread,
            prompt="First message",
            response="First response"
        )
        
        conv2 = Conversation.objects.create(
            thread=thread,
            prompt="Second message", 
            response="Second response"
        )
        
        # Test forward relationship
        assert conv1.thread == thread
        assert conv2.thread == thread
        
        # Test reverse relationship  
        thread_conversations = list(thread.conversation_set.all())
        assert len(thread_conversations) == 2
        assert conv1 in thread_conversations
        assert conv2 in thread_conversations


@pytest.mark.django_db
class TestIntegrationFlow:
    """Integration tests for conversation flow."""

    @pytest.mark.asyncio
    async def test_basic_conversation_flow(self, test_user, mock_genai):
        """Test a basic conversation flow."""
        # Step 1: Generate response (simulates new conversation)
        response = await generate_response("Hello, I need help with my resume")
        assert response == "Mocked AI response"
        
        # Verify the GenAI client was called
        mock_genai.chats.create.assert_called()
        
        # Step 2: Create thread and save conversation
        thread = ConversationsThread.objects.create(
            title="Resume Help",
            user=test_user
        )
        
        Conversation.objects.create(
            thread=thread,
            prompt="Hello, I need help with my resume",
            response=response
        )
        
        # Step 3: Continue conversation with thread_id
        mock_genai.reset_mock()  # Reset call counts
        
        response2 = await generate_response(
            "What should I include?",
            thread_id=thread.id
        )
        
        assert response2 == "Mocked AI response"
        mock_genai.chats.create.assert_called_once()
        
        # Verify history was loaded (should have previous messages)
        call_args = mock_genai.chats.create.call_args
        history = call_args.kwargs.get('history', [])
        assert len(history) == 2  # Previous user + model messages