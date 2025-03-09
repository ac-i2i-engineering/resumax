from google import genai
from google.genai import types
from django.conf import settings
import pathlib
import httpx


def generateContent(promptText, fileUrl=None):
    '''
    This function generates content using the Gemini API
    '''
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    if not fileUrl:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=promptText
        )
        return response.text
    # Retrieve and encode the PDF byte
    filepath = pathlib.Path(str(settings.BASE_DIR)+fileUrl)
    response = client.models.generate_content(
      model="gemini-1.5-flash",
      contents=[
          types.Part.from_bytes(
            data=filepath.read_bytes(),
            mime_type='application/pdf',
          ),
          promptText])

    return response.text


