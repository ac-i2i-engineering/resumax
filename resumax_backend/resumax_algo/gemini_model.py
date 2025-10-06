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
import threading
import os


# Module-level client instance for reuse across functions
_client = None

# Thread-safe in-memory store for chat sessions (per user, per thread)
_chat_sessions = {}
_chat_sessions_lock = threading.Lock()

# Cache for base knowledge file URIs to avoid re-uploading
_base_knowledge_uris = None
_base_knowledge_lock = threading.Lock()

def _get_genai_client():
    """Get or create a shared GenAI client instance"""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not configured")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _get_session_key(thread_id, user_id):
    """Return a unique key for the chat session store."""
    return (user_id, thread_id)

async def _get_or_create_chat_session(thread_id=None, user_id=None):
    """Get or create a persistent Gemini chat session for a user and thread."""
    if not thread_id or not user_id:
        raise Exception("Both thread_id and user_id are required for session persistence.")
    key = _get_session_key(thread_id, user_id)
    with _chat_sessions_lock:
        if key in _chat_sessions:
            return _chat_sessions[key]
    client = _get_genai_client()
    system_content = system_instructions.SYSTEM_PROMPT
    history = await _get_conversation_history(thread_id, max_history=15) if thread_id else []
    
    # Add context files as the first message in history
    context_file_uris = upload_base_knowledge_files()
    context_parts = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in context_file_uris
    ]
    # You can add a clarifying text part if you want
    context_parts.append(types.Part.from_text(text="These are reference documents from Loeb center, always refer to them while responding. They also contains few shots, and other information regarding what we care about"))
    context_message = {
        'role': 'model',
        'parts': context_parts
    }
    history = [context_message] + history
    
    # Improved model configuration for better performance
    chat = client.chats.create(
        model='models/gemini-2.5-flash',
        config={
            "system_instruction": system_content,
            "temperature": 0.7,  
            "top_p": 0.9,     
            "max_output_tokens": 2048 
        },
        history=history
    )
    with _chat_sessions_lock:
        # Limit the number of active sessions to prevent memory issues
        if len(_chat_sessions) >= 20: 
            # Remove oldest session (simple LRU-like behavior)
            oldest_key = next(iter(_chat_sessions))
            del _chat_sessions[oldest_key]
            print(f"Removed oldest chat session to manage memory: {oldest_key}")
        
        _chat_sessions[key] = chat
    return chat


@sync_to_async
def _get_conversation_history(thread_id, max_history=20):
    """Get conversation history from database for chat session with optimizations"""
    try:        
        thread = ConversationsThread.objects.filter(id=thread_id).first()
        if not thread:
            return []
        
        # Optimize query and limit history length for better performance
        conversations = Conversation.objects.filter(
            thread=thread
        ).select_related('thread').prefetch_related('attachedfile_set').order_by('-created_at')[:max_history]
        
        # Reverse to get chronological order after limiting
        conversations = list(reversed(conversations))
        
        history = []
        for conv in conversations:
            if conv.prompt and conv.response:
                # Prepare user message parts (text + any attached files)
                user_parts = [{'text': conv.prompt}]
                
                # Add attached files to user message
                for file in conv.attachedfile_set.all():  # Use prefetched data
                    if file.file_path and file.file_type:
                        client = _get_genai_client()
                        try:
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


async def generate_response(promptText, fileUrls=None, thread_id=None, user_id=None):
    """Generate content using Gemini Chat API with persistent chat session and optimizations."""
    if not promptText or not promptText.strip():
        raise Exception("Prompt text cannot be empty")
    
    try:
        chat = await _get_or_create_chat_session(thread_id, user_id)
        message_parts = [types.Part.from_text(text=promptText)]
        
        # Process file uploads concurrently if provided
        if fileUrls:
            file_parts = await _process_file_uploads(fileUrls)
            message_parts.extend(file_parts)
        
        # Add timeout and retry logic for better reliability
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(chat.send_message, message_parts)
                if response and response.text:
                    return response.text
                else:
                    raise Exception("Empty response from Gemini API")
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise e
                print(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1)  # Brief delay before retry
                
    except Exception as e:
        raise Exception(f"Content generation failed: {e}")


async def _process_file_uploads(fileUrls):
    """Process file uploads concurrently for better performance"""
    if not fileUrls:
        return []
    
    client = _get_genai_client()
    file_parts = []
    
    # Process files concurrently for better performance
    upload_tasks = []
    for file_url in fileUrls:
        file_data = _process_file_url(file_url)
        if file_data:
            upload_tasks.append(_upload_single_file(client, file_data))
    
    if upload_tasks:
        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, types.Part):
                file_parts.append(result)
            elif isinstance(result, Exception):
                print(f"Error in file upload: {result}")
    
    return file_parts


async def _upload_single_file(client, file_data):
    """Upload a single file"""
    file_path, mime_type = file_data
    
    try:
        uploaded = await asyncio.to_thread(client.files.upload, file=file_path)
        return types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type)
    except Exception as e:
        raise Exception(f"Failed to upload {file_path.name}: {e}")

def upload_base_knowledge_files():
    """Upload all files in the base_knowledge folder to Gemini and return their URIs.
    Uses caching to avoid re-uploading the same files multiple times."""
    global _base_knowledge_uris
    
    # Check if we already have cached URIs
    with _base_knowledge_lock:
        if _base_knowledge_uris is not None:
            print("used cached base knowledge")
            return _base_knowledge_uris
    
    # If not cached, upload the files
    base_knowledge_dir = os.path.join(settings.BASE_DIR, 'base_knowledge')
    client = _get_genai_client()
    context_file_uris = []
    
    print("📚 Uploading base knowledge files to Gemini (first time only)...")
    for filename in os.listdir(base_knowledge_dir):
        file_path = os.path.join(base_knowledge_dir, filename)
        if os.path.isfile(file_path):
            try:
                uploaded = client.files.upload(file=pathlib.Path(file_path))
                context_file_uris.append(uploaded.uri)
                print(f"✅ Uploaded {filename}")
            except Exception as e:
                print(f"❌ Error uploading {filename}: {e}")
    
    # Cache the URIs for future use
    with _base_knowledge_lock:
        _base_knowledge_uris = context_file_uris
    
    print(f"📚 Base knowledge files cached ({len(context_file_uris)} files)")
    return context_file_uris


def clear_base_knowledge_cache():
    """Clear the cached base knowledge file URIs. Useful for development or if files change."""
    global _base_knowledge_uris
    with _base_knowledge_lock:
        _base_knowledge_uris = None
    print("🗑️ Base knowledge cache cleared")


def get_cache_stats():
    """Get statistics about current cache usage."""
    with _base_knowledge_lock:
        base_knowledge_count = len(_base_knowledge_uris) if _base_knowledge_uris else 0
    
    return {
        'base_knowledge_files': base_knowledge_count,
        'active_chat_sessions': len(_chat_sessions)
    }