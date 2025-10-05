from google import genai
from google.genai import types
from django.conf import settings
import pathlib
import asyncio
import mimetypes
from asgiref.sync import sync_to_async
from . import system_instructions
from .models import ConversationsThread, Conversation
from pathlib import Path


# Module-level client instance for reuse across functions
_client = None


def _get_genai_client():
    """Get or create a shared GenAI client instance"""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not configured")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


async def _get_or_create_chat_session(thread_id=None):
    """Get chat session with conversation history from database"""
    client = _get_genai_client()
    
    try:
        # Create chat session with system instruction (text only)
        system_content = system_instructions.SYSTEM_PROMPT
        
        # Get conversation history if thread_id provided
        history = await _get_conversation_history(thread_id) if thread_id else None
        
        # Debug: Print history information
        if history:
            print(f"🔄 Loading {len(history)} history messages for thread {thread_id}")
            for i, msg in enumerate(history):
                role = msg.get('role', 'unknown')
                text_preview = msg['parts'][0].get('text', 'no content')[:50] if msg['parts'] else 'no content'
                print(f"  {i+1}. {role}: {text_preview}...")
            print(f"📋 Full history structure: {history}")
        else:
            print(f"📝 No history found for thread {thread_id}" if thread_id else "🆕 New conversation (no thread_id)")
        
        chat = client.chats.create(
            model='gemini-2.5-flash',
            config={"system_instruction": system_content},
            history=history
        )
            
        return chat
        
    except Exception as e:
        raise Exception(f"Failed to create chat session: {e}")


@sync_to_async
def _get_conversation_history(thread_id):
    """Get conversation history from database for chat session"""
    try:
        from .models import AttachedFile
        
        thread = ConversationsThread.objects.filter(id=thread_id).first()
        if not thread:
            return []
        
        conversations = Conversation.objects.filter(thread=thread).order_by('created_at')
        
        history = []
        for conv in conversations:
            if conv.prompt and conv.response:
                # Prepare user message parts (text + any attached files)
                user_parts = [{'text': conv.prompt}]
                
                # Add attached files to user message
                attached_files = AttachedFile.objects.filter(conversation=conv)
                for file in attached_files:
                    if file.file_path and file.file_type:
                        # Create file part for Google GenAI
                        client = _get_genai_client()
                        try:
                            # Get the full file path
                            full_path = pathlib.Path(settings.MEDIA_ROOT) / file.stored_filename
                            if full_path.exists():
                                uploaded = client.files.upload(file=full_path)
                                file_part = {'file_data': {'file_uri': uploaded.uri, 'mime_type': file.file_type}}
                                user_parts.append(file_part)
                                print(f"📎 Added file {file.original_filename} to history")
                        except Exception as e:
                            print(f"⚠️ Failed to add file {file.original_filename} to history: {e}")
                
                # Add user message with all parts
                history.append({
                    'role': 'user',
                    'parts': user_parts
                })
                
                # Add model response  
                history.append({
                    'role': 'model',
                    'parts': [{'text': conv.response}]
                })
                
        return history
        
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []


def _get_mime_type(file_path):
    """Get MIME type for a file"""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/pdf'


def _process_file_url(file_url):
    """Process a single file URL"""
    relative_path = file_url.replace(settings.MEDIA_URL, '')
    full_path = pathlib.Path(settings.MEDIA_ROOT) / relative_path
    
    if full_path.exists():
        return (full_path, _get_mime_type(full_path))
    return None


async def generate_response(promptText, fileUrls=None, thread_id=None):
    """Generate content using Gemini Chat API"""
    if not promptText or not promptText.strip():
        raise Exception("Prompt text cannot be empty")
    
    try:
        chat = await _get_or_create_chat_session(thread_id)
        
        message_parts = [types.Part.from_text(text=promptText)]
        
        # Handle file uploads if provided
        if fileUrls:
            file_parts = await _process_file_uploads(fileUrls)
            message_parts.extend(file_parts)
        
        response = chat.send_message(message_parts)
        
        if not response or not response.text:
            raise Exception("Empty response from Gemini API")
            
        return response.text
        
    except Exception as e:
        raise Exception(f"Content generation failed: {e}")


async def _process_file_uploads(fileUrls):
    """Process file uploads"""
    if not fileUrls:
        return []
    
    client = _get_genai_client()
    file_parts = []
    
    for file_url in fileUrls:
        file_data = _process_file_url(file_url)
        if file_data:
            file_path, mime_type = file_data
            try:
                uploaded = client.files.upload(file=file_path)
                file_part = types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type)
                file_parts.append(file_part)
            except Exception as e:
                print(f"Error uploading {file_path.name}: {e}")
    
    return file_parts