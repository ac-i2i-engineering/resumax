from google import genai
from google.genai import types
from django.conf import settings
import pathlib
import asyncio
import mimetypes

async def generate_response(promptText, fileUrls=None):
    '''
    This function generates content using the Gemini API
    '''
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    if not fileUrls:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=promptText
        )
        return response.text
        
    # Convert URLs to actual file paths using MEDIA_ROOT
    file_data = []  # Store both path and MIME type
    for fileUrl in fileUrls:
        # Remove the MEDIA_URL prefix and construct the full file path
        relative_path = fileUrl.replace(settings.MEDIA_URL, '')
        full_path = pathlib.Path(settings.MEDIA_ROOT) / relative_path
        
        # Check if file exists before adding to processing list
        if full_path.exists():
            # Determine MIME type from file extension
            mime_type, _ = mimetypes.guess_type(str(full_path))
            if not mime_type:
                # Fallback to application/pdf for unknown types
                mime_type = 'application/pdf'
            file_data.append((full_path, mime_type))
        else:
            print(f"Warning: File not found: {full_path}")
    
    # If no valid files found, process text only
    if not file_data:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=promptText
        )
        return response.text
    
    # Process files
    try:
        read_file_tasks = [read_file_async(fp) for fp, _ in file_data]
        file_contents = await asyncio.gather(*read_file_tasks)
        
        # Create file parts with correct MIME types
        file_parts = []
        for i, content in enumerate(file_contents):
            _, mime_type = file_data[i]
            file_parts.append(types.Part.from_bytes(data=content, mime_type=mime_type))
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=file_parts + [promptText]  # Include `promptText` after file parts
        )
        return response.text
    except Exception as e:
        print(f"Error processing files: {e}")
        # Fallback to text-only processing
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=promptText
        )
        return response.text

async def read_file_async(filepath):
        return await asyncio.to_thread(filepath.read_bytes)

