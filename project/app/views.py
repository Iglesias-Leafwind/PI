from django.shortcuts import render
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm

def index(request):
    folders = []  # folders should be Folder.objects.all()

    if request.method == 'POST':
        query = SearchForm(request.POST)
        image = SearchForImageForm(request.POST, request.FILES)
        pathf = EditFoldersForm(request.POST)
        results = []
        if query.is_valid() and query.cleaned_data['query']: # search bar input was valid and not null
            query_array = query.cleaned_data['query'].split(" ")
            # use the query_array to search by tags and pass them as 'results'
            query = SearchForm()
            return render(request, "index.html", {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders, 'results': results}) #return new index with results this time and cleaned form
        elif image.is_valid() and image.cleaned_data["image"]: # if search by image file exists
            image = image.cleaned_data["image"]
            # use the image to process image and look for similar images in model
            image = SearchForImageForm()
            return render(request, "index.html", {'form': query, 'image_form': image,  'path_form': pathf, 'folders': folders, 'results': results}) #return new index with results this time and cleaned form
        elif pathf.is_valid() and pathf.cleaned_data["path"]: # if path of new folder has a name, then it exists
            # new = Folder(url = pathf.path)
            # new.save()
            pathf = EditFoldersForm()
            return render(request, "index.html", {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders,'results': results})  # return new index with results this time and cleaned form
        else: # the form filled had a mistake
            form = SearchForm()
            image = SearchForImageForm()
            pathf = EditFoldersForm()
            return render(request, 'index.html', {'form': form, 'image_form': image,  'path_form': pathf, 'folders': folders, 'results': []})

    else:   # first time in the page - no forms filled
        form = SearchForm()
        image = SearchForImageForm()
        path = EditFoldersForm()
        return render(request, 'index.html', {'form': form, 'image_form': image,  'path_form': path, 'folders': folders, 'results': []})
