from django.contrib.auth.decorators import login_required
from django.forms import ValidationError
from rest_framework.parsers import MultiPartParser
from resumax_algo.models import AttachedFile, ConversationsThread, Conversation
from rest_framework.decorators import api_view,parser_classes
from rest_framework.response import Response
from resumax_algo.gemini_model import generate_response
from .serializers import AttachedFileSerializer, ConversationSerializer, ConversationsThreadSerializer
from django.core.files.storage import FileSystemStorage
import asyncio
import uuid
import os

# Create your views here.
@login_required
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])
def conversations(request, thread_id):
    user = request.user
    if request.method == 'GET':
        try:
            currentThread = ConversationsThread.objects.get(user=user, id=thread_id)
        except ConversationsThread.DoesNotExist:
            return Response({"error": "Thread not found"}, status=404)
        context = {
                "conversations": [
                    {
                        "prompt": conversation.prompt,
                        "response": conversation.response,
                        "attachedFiles": [ attachedFile.original_filename for attachedFile in AttachedFile.objects.filter(conversation=conversation.id)]
                    }
                    for conversation in Conversation.objects.filter(thread=currentThread)
                ]
            }
        return Response(context)
    if request.method == 'POST':
        # Get and validate prompt text
        promptText = request.data.get("prompt-text")
        if not promptText or not promptText.strip():
            return Response({"error": "Prompt text is required and cannot be empty"}, status=400)
        
        # Create a new thread if the request thread_id is 0
        if thread_id == 0:       
            title = promptText[0:20]
            thread = ConversationsThread.objects.create(title=title, user=user)
            thread_id = thread.id
        # save conversation
        promptAttachedFiles = request.FILES.getlist("prompt-file")
        # if no file is provided
        if not promptAttachedFiles:
            # Generate response using Gemini
            try:
                response = asyncio.run(generate_response(promptText))
            except Exception as e:
                return Response({"error": str(e)}, status=500)
            # Save conversation to the database
            promptData = {
                "prompt": promptText,
                "response": response,
                 "thread": thread_id
            }
            promptSerializer = ConversationSerializer(data = promptData)
            if promptSerializer.is_valid():
                conversation = promptSerializer.save()
            else:
                return Response({"error": promptSerializer.errors}, status=400)
            # Return response
            return Response({"response": response})
        # # if file is provided
        #upload file to user_uploads folder (configured in settings) with user-specific directories
        uploaded_file_data = []  # Store both original and stored filenames
        for promptAttachedFile in promptAttachedFiles:
            validate_file(promptAttachedFile)
            # Get file extension
            file_extension = os.path.splitext(promptAttachedFile.name)[1]
            # Generate unique filename while preserving extension
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # Create user-specific directory structure within MEDIA_ROOT
            user_dir = f"user_{user.id}"
            user_upload_path = os.path.join(user_dir, unique_filename)
            
            # Use default FileSystemStorage (uses settings.MEDIA_ROOT and MEDIA_URL)
            fs = FileSystemStorage()
            stored_filename = fs.save(user_upload_path, promptAttachedFile)
            file_url = fs.url(stored_filename)
            
            uploaded_file_data.append({
                'original_filename': promptAttachedFile.name,
                'stored_filename': stored_filename,
                'file_url': file_url,
                'file_size': promptAttachedFile.size,
                'file_type': promptAttachedFile.content_type
            })
        # Generate response
        try:
            # Generate response considering attached files
            file_urls = [file_data['file_url'] for file_data in uploaded_file_data]
            response = asyncio.run(generate_response(promptText, file_urls))
            
            # Truncate response if it's too long for the database
            if len(response) > 20000:
                response = response[:19950] + "... [Response truncated]"
                
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        # Save conversation to the database
        promptData = {
                "prompt": promptText,
                "response": response,
                 "thread": thread_id
            }
        promptSerializer = ConversationSerializer(data = promptData)
        if promptSerializer.is_valid():
            conversation = promptSerializer.save()
            # save files to the database
            original_filenames = []
            for file_data in uploaded_file_data:
                fileData = {
                    "conversation": conversation.id, 
                    "original_filename": file_data['original_filename'],
                    "stored_filename": file_data['stored_filename'],
                    "file_path": file_data['file_url'],
                    "file_size": file_data['file_size'],
                    "file_type": file_data['file_type'],
                    "processing_status": "completed"
                }
                fileSerializer = AttachedFileSerializer(data=fileData)
                if fileSerializer.is_valid():
                    fileSerializer.save()
                    original_filenames.append(file_data['original_filename'])
                else:               
                    return Response({"error": fileSerializer.errors}, status=400)
            return Response({"response": response, "attachedFiles": original_filenames})
        else:
            return Response({"error": promptSerializer.errors}, status=400)
    

@login_required
@api_view(['GET'])
def get_all_threads(request):
    user = request.user
    allThreads = ConversationsThread.objects.filter(user=user)
    # Reverse the order of threads to start from the most recent
    context = {
        "threads": [
            {
                "id": thread.id,
                "title": thread.title,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at
            }
            for thread in allThreads
        ].__reversed__()
    }
    return Response(context)

@login_required
@api_view(['DELETE'])
def delete_thread(request, thread_id):
    user = request.user
    try:
        thread = ConversationsThread.objects.get(user=user, id=thread_id)
    except ConversationsThread.DoesNotExist:
        return Response({"error": "Thread not found"}, status=404)
    thread.delete()
    return Response({"message": "Thread deleted successfully"}, status=200)

def validate_file(file):  
    allowed_types = ['application/pdf']  
    if file.content_type not in allowed_types:  
        raise ValidationError('Invalid file type')  
    if file.size > 5242880:  # 5MB limit  
        raise ValidationError('File too large')  
    return True 

def secure_filename(filename):
    return filename.replace(" ", "_")
# TODO: add a functionality to vectorize all the messages in the same thread and send them with the prompt to the server