from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse

import os

# Create your views here.
def index(request):
    if request.method == 'POST' and request.FILES['file']:
        print('FILE UPLOADED')
        file = request.FILES['file']
        fs = FileSystemStorage()
        file_path = fs.save(file.name, file)
        file_url = fs.url(file_path)

        # Clean up the uploaded file
        os.remove(file_path)
        
        return render(request, 'resumax_algo/index.html')

    return render(request, 'resumax_algo/index.html')