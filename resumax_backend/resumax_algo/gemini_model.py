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
from functools import lru_cache
import time

# Module-level client instance for reuse across functions
_client = None

# Thread-safe in-memory store for chat sessions (per user, per thread)
_chat_sessions = {}
_chat_sessions_lock = threading.Lock()
_chat_access_times = {}  # Track access times for better LRU

# Cache for base knowledge file URIs to avoid re-uploading
_base_knowledge_uris = None
_base_knowledge_lock = threading.Lock()

# Cache constants at module level instead of using @lru_cache
_SYSTEM_INSTRUCTION = system_instructions.SYSTEM_PROMPT
_MODEL_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_output_tokens": 2048
}

def _get_genai_client():
    """Get or create a shared GenAI client instance"""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not configured")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

@lru_cache(maxsize=100)
def _get_mime_type_by_extension(file_extension):
    """Cached MIME type detection by file extension - much more efficient"""
    if not file_extension:
        raise Exception("file mimetype couldn't be guessed without file extension")
    
    # Ensure extension starts with dot
    if not file_extension.startswith('.'):
        file_extension = '.' + file_extension
    
    mime_type, _ = mimetypes.guess_type(f"dummy{file_extension}")
    return mime_type or 'application/pdf'

def _get_session_key(thread_id, user_id):
    """Return a unique key for the chat session store."""
    return (user_id, thread_id)

async def _get_or_create_chat_session(thread_id=None, user_id=None):
    """Get or create a persistent Gemini chat session with improved LRU management."""
    if not thread_id or not user_id:
        raise Exception("Both thread_id and user_id are required for session persistence.")
    
    key = _get_session_key(thread_id, user_id)
    current_time = time.time()
    
    with _chat_sessions_lock:
        if key in _chat_sessions:
            _chat_access_times[key] = current_time  # Update access time
            return _chat_sessions[key]
    
    client = _get_genai_client()
    # Use direct module variable instead of cached function
    system_content = _SYSTEM_INSTRUCTION
    history = await _get_conversation_history(thread_id, max_history=15) if thread_id else []
    
    # Load base knowledge files (keep sync for now, but optimize)
    context_file_uris = await asyncio.to_thread(upload_base_knowledge_files)
    context_parts = [
        types.Part.from_uri(file_uri=uri, mime_type="application/pdf")
        for uri in context_file_uris
    ]
    context_parts.append(types.Part.from_text(
        text="These are reference documents from Loeb center, always refer to them while responding. They also contains few shots, and other information regarding what we care about"
    ))
    
    context_message = {'role': 'model', 'parts': context_parts}
    history = [context_message] + history
    
    # Create chat with direct config access
    chat = client.chats.create(
        model='models/gemini-2.5-flash',
        config={
            "system_instruction": system_content,
            **_MODEL_CONFIG  # Use direct module variable
        },
        history=history
    )
    
    with _chat_sessions_lock:
        # Improved LRU cleanup - remove least recently used
        if len(_chat_sessions) >= 20:
            if _chat_access_times:  # Safety check
                oldest_key = min(_chat_access_times.keys(), 
                               key=lambda k: _chat_access_times[k])
                del _chat_sessions[oldest_key]
                del _chat_access_times[oldest_key]
                print(f"🧹 Removed LRU session: {oldest_key}")
        
        _chat_sessions[key] = chat
        _chat_access_times[key] = current_time
    
    return chat

@sync_to_async
def _get_conversation_history(thread_id, max_history=20):
    """Get conversation history from database for chat session with optimizations"""
    try:        
        thread = ConversationsThread.objects.filter(id=thread_id).first()
        if not thread:
            return []
        
        conversations = Conversation.objects.filter(
            thread=thread
        ).select_related('thread').prefetch_related('attachedfile_set').order_by('-created_at')[:max_history]
        
        conversations = list(reversed(conversations))
        
        history = []
        for conv in conversations:
            if conv.prompt and conv.response:
                user_parts = [{'text': conv.prompt}]
                
                # Add attached files to user message
                for file in conv.attachedfile_set.all():
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
                
                history.append({'role': 'user', 'parts': user_parts})
                history.append({'role': 'model', 'parts': [{'text': conv.response}]})
                
        return history
        
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

def _process_file_url_sync(file_url):
    """Synchronous file URL processing (optimized with extension-based MIME detection)"""
    relative_path = file_url.replace(settings.MEDIA_URL, '')
    full_path = pathlib.Path(settings.MEDIA_ROOT) / relative_path
    
    try:
        if full_path.exists():
            extension = pathlib.Path(full_path).suffix.lower()  # Extract extension
            mime_type = _get_mime_type_by_extension(extension)  # Cache by extension
            return (full_path, mime_type)
    except Exception as e:
        print(f"Error checking file {full_path}: {e}")
    
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
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(chat.send_message, message_parts)
                if response and response.text:
                    return response.text
                else:
                    last_error = Exception("Empty response from Gemini API")
                    if attempt == max_retries - 1:
                        raise last_error
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise e
                print(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
    except Exception as e:
        raise Exception(f"Content generation failed: {e}")

async def _process_file_uploads(fileUrls):
    """Process file uploads with concurrent processing"""
    if not fileUrls:
        return []
    
    client = _get_genai_client()
    
    # Process file URLs concurrently using thread pool
    file_data_tasks = [
        asyncio.to_thread(_process_file_url_sync, file_url) 
        for file_url in fileUrls
    ]
    file_data_results = await asyncio.gather(*file_data_tasks, return_exceptions=True)
    
    # Prepare upload tasks for valid files
    upload_tasks = []
    for result in file_data_results:
        if result and not isinstance(result, Exception):
            upload_tasks.append(_upload_single_file(client, result))
    
    # Upload files concurrently
    if upload_tasks:
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        file_parts = []
        for result in upload_results:
            if isinstance(result, types.Part):
                file_parts.append(result)
            elif isinstance(result, Exception):
                print(f"Error in file upload: {result}")
        return file_parts
    
    return []

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
    
    with _base_knowledge_lock:
        if _base_knowledge_uris is not None:
            print("📚 Using cached base knowledge files")
            return _base_knowledge_uris
    
    base_knowledge_dir = os.path.join(settings.BASE_DIR, 'base_knowledge')
    client = _get_genai_client()
    context_file_uris = []
    
    try:
        if not os.path.exists(base_knowledge_dir):
            print(f"❌ Base knowledge directory not found: {base_knowledge_dir}")
            return []
            
        print("📚 Uploading base knowledge files to Gemini (first time only)...")
        files = [f for f in os.listdir(base_knowledge_dir) 
                if os.path.isfile(os.path.join(base_knowledge_dir, f))]
        
        for filename in files:
            file_path = os.path.join(base_knowledge_dir, filename)
            try:
                uploaded = client.files.upload(file=pathlib.Path(file_path))
                context_file_uris.append(uploaded.uri)
                print(f"✅ Uploaded {filename}")
            except Exception as e:
                print(f"❌ Error uploading {filename}: {e}")
        
        # Cache the URIs
        with _base_knowledge_lock:
            _base_knowledge_uris = context_file_uris
        
        print(f"📚 Base knowledge files cached ({len(context_file_uris)} files)")
        return context_file_uris
        
    except Exception as e:
        print(f"❌ Error in base knowledge upload: {e}")
        return []

def clear_base_knowledge_cache():
    """Clear the cached base knowledge file URIs."""
    global _base_knowledge_uris
    with _base_knowledge_lock:
        _base_knowledge_uris = None
    print("🗑️ Base knowledge cache cleared")

def get_cache_stats():
    """Get statistics about current cache usage with enhanced info."""
    with _base_knowledge_lock:
        base_knowledge_count = len(_base_knowledge_uris) if _base_knowledge_uris else 0
    
    with _chat_sessions_lock:
        active_sessions = len(_chat_sessions)
        oldest_session_age = 0
        if _chat_access_times:
            current_time = time.time()
            oldest_access = min(_chat_access_times.values())
            oldest_session_age = current_time - oldest_access
    
    return {
        'base_knowledge_files': base_knowledge_count,
        'active_chat_sessions': active_sessions,
        'oldest_session_age_seconds': round(oldest_session_age, 2),
        'mime_type_cache_info': _get_mime_type_by_extension.cache_info(),
        # Removed unnecessary cache_info calls for module constants
    }