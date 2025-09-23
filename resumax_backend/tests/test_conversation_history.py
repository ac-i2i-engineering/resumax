"""
Test cases for conversation history functionality.

This module tests the conversation history feature including:
- Chat session creation and management
- History loading and persistence
- File attachment handling in conversations
- Thread-based conversation continuity
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from resumax_algo.models import ConversationsThread, Conversation, AttachedFile
from resumax_algo.gemini_model import generate_response, _get_conversation_history


@pytest.fixture
def test_user(django_user_model):
    """Create a test user for conversation tests."""
    return django_user_model.objects.create_user(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def test_thread(test_user):
    """Create a test conversation thread."""
    return ConversationsThread.objects.create(
        title="Test Conversation Thread",
        user=test_user
    )


@pytest.fixture
def sample_conversations(test_thread):
    """Create sample conversations for testing history."""
    conversations = []
    
    # First conversation
    conv1 = Conversation.objects.create(
        thread=test_thread,
        prompt="Hi, my name is John and I'm a software engineer",
        response="Hello John! Nice to meet you. As a software engineer, I can help you create an impressive resume that highlights your technical skills and experience."
    )
    conversations.append(conv1)
    
    # Second conversation
    conv2 = Conversation.objects.create(
        thread=test_thread,
        prompt="What should I include in my resume?",
        response="For a software engineer resume, you should include: technical skills, programming languages, projects, work experience, and education. Let me help you structure each section."
    )
    conversations.append(conv2)
    
    return conversations


@pytest.fixture
def mock_genai_client():
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


class TestConversationHistory:
    """Test cases for conversation history functionality."""

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_get_conversation_history_empty_thread(self, test_thread):
        """Test getting history from an empty thread."""
        history = await _get_conversation_history(test_thread.id)
        
        assert history == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_get_conversation_history_with_conversations(self, sample_conversations):
        """Test getting history from a thread with conversations."""
        thread_id = sample_conversations[0].thread.id
        
        history = await _get_conversation_history(thread_id)
        
        assert len(history) == 4  # 2 conversations = 4 messages (user + model each)
        
        # Check first user message
        assert history[0]['role'] == 'user'
        assert 'John' in history[0]['parts'][0]['text']
        assert 'software engineer' in history[0]['parts'][0]['text']
        
        # Check first model response
        assert history[1]['role'] == 'model'
        assert 'Hello John' in history[1]['parts'][0]['text']
        
        # Check second user message
        assert history[2]['role'] == 'user'
        assert 'What should I include' in history[2]['parts'][0]['text']
        
        # Check second model response
        assert history[3]['role'] == 'model'
        assert 'technical skills' in history[3]['parts'][0]['text']

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_get_conversation_history_nonexistent_thread(self):
        """Test getting history from a non-existent thread."""
        history = await _get_conversation_history(99999)
        
        assert history == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_generate_response_new_conversation(self, mock_genai_client):
        """Test generating response for a new conversation (no thread_id)."""
        response = await generate_response("Hello, I'm a new user")
        
        assert response == "Mocked AI response"
        mock_genai_client.chats.create.assert_called_once()
        
        # Verify no history was passed
        call_args = mock_genai_client.chats.create.call_args
        assert 'history' not in call_args.kwargs or call_args.kwargs['history'] == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_generate_response_with_thread_history(self, sample_conversations, mock_genai_client):
        """Test generating response with conversation history."""
        thread_id = sample_conversations[0].thread.id
        
        response = await generate_response(
            "Remember my name from earlier?", 
            thread_id=thread_id
        )
        
        assert response == "Mocked AI response"
        mock_genai_client.chats.create.assert_called_once()
        
        # Verify history was passed
        call_args = mock_genai_client.chats.create.call_args
        assert 'history' in call_args.kwargs
        assert len(call_args.kwargs['history']) == 4  # 2 conversations = 4 messages

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
    async def test_conversation_history_with_file_attachments(self, test_thread, mock_genai_client):
        """Test conversation history includes file attachments."""
        # Create a conversation with file attachment
        conv = Conversation.objects.create(
            thread=test_thread,
            prompt="Please review my resume",
            response="I'd be happy to review your resume. Let me analyze it for you."
        )
        
        # Create attached file
        AttachedFile.objects.create(
            conversation=conv,
            filename="resume.pdf",
            file_path="/test/path/resume.pdf"
        )
        
        history = await _get_conversation_history(test_thread.id)
        
        assert len(history) == 2  # user + model messages
        
        # Check that user message includes file attachment
        user_message = history[0]
        assert user_message['role'] == 'user'
        assert len(user_message['parts']) == 2  # text + file
        assert user_message['parts'][0]['text'] == "Please review my resume"
        assert 'file_data' in user_message['parts'][1]

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_file_upload_in_generate_response(self, test_thread, mock_genai_client):
        """Test file upload functionality in generate_response."""
        mock_file_url = "http://example.com/test.pdf"
        
        response = await generate_response(
            "Analyze this document",
            fileUrls=[mock_file_url],
            thread_id=test_thread.id
        )
        
        assert response == "Mocked AI response"
        
        # Verify file was uploaded to GenAI
        mock_genai_client.files.upload.assert_called_once()
        
        # Verify chat was created with file in message
        mock_genai_client.chats.create.assert_called_once()


class TestConversationAPI:
    """Test cases for conversation API endpoints."""

    @pytest.mark.django_db
    def test_conversation_api_requires_auth(self, client):
        """Test that conversation API requires authentication."""
        response = client.post(reverse('conversations'), {
            'prompt': 'Test message'
        })
        
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    @pytest.mark.django_db
    def test_conversation_api_with_auth(self, client, test_user):
        """Test conversation API with authenticated user."""
        client.force_login(test_user)
        
        with patch('resumax_api.views.generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test AI response"
            
            response = client.post(reverse('conversations'), {
                'prompt': 'Hello, test message'
            })
            
            assert response.status_code == 200
            mock_generate.assert_called_once()

    @pytest.mark.django_db
    def test_conversation_api_with_thread_id(self, client, test_user, test_thread):
        """Test conversation API with existing thread ID."""
        client.force_login(test_user)
        
        with patch('resumax_api.views.generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test AI response with history"
            
            response = client.post(reverse('conversations'), {
                'prompt': 'Continue our conversation',
                'thread_id': test_thread.id
            })
            
            assert response.status_code == 200
            
            # Verify generate_response was called with thread_id
            call_args = mock_generate.call_args
            assert call_args.kwargs.get('thread_id') == test_thread.id

    @pytest.mark.django_db
    def test_conversation_api_with_file_upload(self, client, test_user):
        """Test conversation API with file upload."""
        client.force_login(test_user)
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt", 
            b"This is a test file content",
            content_type="text/plain"
        )
        
        with patch('resumax_api.views.generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "File analyzed successfully"
            
            response = client.post(reverse('conversations'), {
                'prompt': 'Please analyze this file',
                'file': test_file
            })
            
            assert response.status_code == 200
            mock_generate.assert_called_once()
            
            # Verify fileUrls parameter was passed
            call_args = mock_generate.call_args
            assert 'fileUrls' in call_args.kwargs
            assert call_args.kwargs['fileUrls'] is not None


class TestConversationPersistence:
    """Test cases for conversation data persistence."""

    @pytest.mark.django_db
    def test_conversation_saved_to_database(self, test_thread):
        """Test that conversations are properly saved to database."""
        initial_count = Conversation.objects.filter(thread=test_thread).count()
        
        # This would normally be called by the API view
        conversation = Conversation.objects.create(
            thread=test_thread,
            prompt="Test prompt",
            response="Test response"
        )
        
        assert Conversation.objects.filter(thread=test_thread).count() == initial_count + 1
        assert conversation.prompt == "Test prompt"
        assert conversation.response == "Test response"
        assert conversation.thread == test_thread

    @pytest.mark.django_db
    def test_attached_file_relationship(self, test_thread):
        """Test the relationship between conversations and attached files."""
        conversation = Conversation.objects.create(
            thread=test_thread,
            prompt="Test with file",
            response="File received"
        )
        
        attached_file = AttachedFile.objects.create(
            conversation=conversation,
            filename="test.pdf",
            file_path="/test/path/test.pdf"
        )
        
        # Test forward relationship
        assert attached_file.conversation == conversation
        
        # Test reverse relationship
        assert conversation.attachedfile_set.first() == attached_file

    @pytest.mark.django_db
    def test_thread_cascade_deletion(self, test_thread, sample_conversations):
        """Test that deleting a thread cascades to conversations and files."""
        thread_id = test_thread.id
        
        # Add a file to one conversation
        AttachedFile.objects.create(
            conversation=sample_conversations[0],
            filename="test.pdf", 
            file_path="/test/path/test.pdf"
        )
        
        # Verify data exists
        assert Conversation.objects.filter(thread_id=thread_id).count() == 2
        assert AttachedFile.objects.filter(conversation__thread_id=thread_id).count() == 1
        
        # Delete thread
        test_thread.delete()
        
        # Verify cascade deletion
        assert Conversation.objects.filter(thread_id=thread_id).count() == 0
        assert AttachedFile.objects.filter(conversation__thread_id=thread_id).count() == 0


@pytest.mark.django_db
class TestConversationHistoryIntegration:
    """Integration tests for the complete conversation history flow."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, test_user, mock_genai_client):
        """Test a complete conversation flow with history persistence."""
        # Step 1: Start new conversation
        response1 = await generate_response("Hi, I'm John, a software engineer")
        assert response1 == "Mocked AI response"
        
        # Step 2: Create thread and save first conversation
        thread = ConversationsThread.objects.create(
            title="John's Resume Help",
            user=test_user
        )
        
        Conversation.objects.create(
            thread=thread,
            prompt="Hi, I'm John, a software engineer",
            response=response1
        )
        
        # Step 3: Continue conversation with history
        response2 = await generate_response(
            "What should I put in my resume?",
            thread_id=thread.id
        )
        assert response2 == "Mocked AI response"
        
        # Verify history was loaded
        call_args = mock_genai_client.chats.create.call_args
        assert 'history' in call_args.kwargs
        assert len(call_args.kwargs['history']) == 2  # Previous user + model messages
        
        # Step 4: Save second conversation
        Conversation.objects.create(
            thread=thread,
            prompt="What should I put in my resume?",
            response=response2
        )
        
        # Step 5: Third message should have full history
        response3 = await generate_response(
            "Do you remember my name?",
            thread_id=thread.id
        )
        
        # Verify full history was loaded
        call_args = mock_genai_client.chats.create.call_args
        assert len(call_args.kwargs['history']) == 4  # All previous messages