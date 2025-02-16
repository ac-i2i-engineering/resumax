from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse

import os

# Create your views here.
@login_required
def index(request):
    context = {'username': request.user.username}
    if request.method == 'POST' and request.FILES['file']:
        print('FILE UPLOADED')
        file = request.FILES['file']
        fs = FileSystemStorage()
        file_path = fs.save(file.name, file)
        file_url = fs.url(file_path)

        # Clean up the uploaded file
        os.remove(file_path)
        
        return render(request, 'resumax_algo/index.html',context)

    return render(request, 'resumax_algo/index.html',context)