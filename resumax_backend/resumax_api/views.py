from django.contrib.auth.decorators import login_required
from django.forms import ValidationError
from rest_framework.parsers import MultiPartParser
from resumax_algo.models import AttachedFile, ConversationsThread, Conversation
from rest_framework.decorators import api_view,parser_classes
from rest_framework.response import Response
from resumax_algo.gemini_model import generate_response
from .serializers import AttachedFileSerializer, ConversationSerializer, ConversationsThreadSerializer
from django.core.files.storage import FileSystemStorage
from resumax_algo import retriever
from resumax_backend.settings import USE_RETRIEVAL_BASED_RESPONSE
import asyncio

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
                        "attachedFiles": [ attachedFile.fileName for attachedFile in AttachedFile.objects.filter(conversation=conversation.id)]
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
            # Generate response
            try:
                if USE_RETRIEVAL_BASED_RESPONSE:
                    response = retriever.generate_response(promptText)
                else:
                    response = asyncio.run(generate_response(promptText))
                
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
            else:
                return Response({"error": promptSerializer.errors}, status=400)
            # Return response
            return Response({"response": response})
        # # if file is provided
        #upload file to media folder
        uploaded_file_urls = [] 
        for promptAttachedFile in promptAttachedFiles:
            validate_file(promptAttachedFile)
            # sanitize file name    
            safe_filename = secure_filename(promptAttachedFile.name)
            fs = FileSystemStorage()
            filename = fs.save(safe_filename, promptAttachedFile)
            uploaded_file_urls.append(fs.url(filename))
        # Generate response
        try:
            # Generate response considering attached files
            response = asyncio.run(generate_response(promptText, uploaded_file_urls))
            
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
            fileNames = [ url.split("/")[-1] for url in uploaded_file_urls]
            for fileName in fileNames:
                fileData = {
                    "conversation": conversation.id, 
                    "fileName": fileName
                }
                fileSerializer = AttachedFileSerializer(data=fileData)
                if fileSerializer.is_valid():
                    fileSerializer.save() 
                else:               
                    return Response({"error": fileSerializer.errors}, status=400)
            return Response({"response": response, "attachedFiles": fileNames})
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