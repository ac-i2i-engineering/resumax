from google import genai
from google.genai import types
from django.conf import settings
import pathlib
import asyncio

async def generateContent(promptText, fileUrls=None):
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
    # Retrieve and encode the PDF byte
    
    file_paths = [pathlib.Path(str(settings.BASE_DIR) + fileUrl) for fileUrl in fileUrls]  # Assuming `fileUrls` is a list of file paths
    read_file_tasks = [read_file_async(fp) for fp in file_paths]
    file_contents = await asyncio.gather(*read_file_tasks)
    file_parts = [types.Part.from_bytes(data=content, mime_type='application/pdf') for content in file_contents]
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=file_parts + [promptText]  # Include `promptText` after file parts
    )

    return response.text

async def read_file_async(filepath):
        return await asyncio.to_thread(filepath.read_bytes)

