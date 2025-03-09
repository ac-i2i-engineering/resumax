from django.contrib.auth.decorators import login_required
from rest_framework.parsers import MultiPartParser
from resumax_algo.models import ConversationsThread, Conversation
from rest_framework.decorators import api_view,parser_classes
from rest_framework.response import Response
from resumax_algo.aiModel import generateContent
from .serializers import AttachedFileSerializer, ConversationSerializer
from django.core.files.storage import FileSystemStorage
from django.conf import settings
# Create your views here.
@login_required
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])
def get_conversations(request, thread_id):
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
                    }
                    for conversation in Conversation.objects.filter(thread=currentThread)
                ]
            }
        return Response(context)
    if request.method == 'POST':        
        promptText = request.data.get("prompt-text")
        promptFile = request.FILES.get("prompt-file")
        # if no file is provided
        if not promptFile:
            # Generate response
            try:
                response = generateContent(promptText)
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
            return Response({"text": response})
        # # if file is provided
        #upload file to media folder
        fs = FileSystemStorage()
        filename = fs.save(promptFile.name, promptFile)
        uploaded_file_url = fs.url(filename)
        # Generate response
        try:
            response = generateContent(promptText, uploaded_file_url)
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
            # save file to the database
            fileData = {
                "Conversation": conversation.id, 
                "fileName": filename
            }
            fileSerializer = AttachedFileSerializer(data=fileData)
            if fileSerializer.is_valid():
                fileSerializer.save()                
                return Response({"text": response})
            return Response({"error": fileSerializer.errors}, status=400)
        else:
            return Response({"error": promptSerializer.errors}, status=400)
    

@login_required
@api_view(['GET'])
def threads(request):
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
