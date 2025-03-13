from google import genai
from google.genai import types
from django.conf import settings
import pathlib

def generateContent(promptText, fileUrls=None):
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
    filepaths = [pathlib.Path(str(settings.BASE_DIR) + fileUrl) for fileUrl in fileUrls]  # Assuming `fileUrls` is a list of file paths
    file_parts = [
        types.Part.from_bytes(
            data=filepath.read_bytes(),
            mime_type='application/pdf'
        ) for filepath in filepaths
    ]
    response = client.models.generate_content(
      model="gemini-1.5-flash",
      contents=file_parts + [promptText]  # Include `promptText` after file parts
    )

    return response.text


