from django.shortcuts import render
from app.forms import SearchForm, SearchForImageForm

def index(request):
    if request.method == 'POST':
        query = SearchForm(request.POST)
        image = SearchForImageForm(request.POST, request.FILES)
        if query.is_valid() and query.cleaned_data['query']:
            query_array = query.cleaned_data['query'].split(" ")
            # use the query_array to search by tags and pass them as 'results'
            query = SearchForm()
            return render(request, "index.html", {'form': query, 'image_form': image, 'results': {}})
        elif image.is_valid():
            image = image.cleaned_data["image"]
            # use the image to process image and look for similar images in model
            image = SearchForImageForm()
            return render(request, "index.html", {'form': query, 'image_form': image, 'results' : {}})
        else:
            form = SearchForm()
            image = SearchForImageForm()
            return render(request, 'index.html', {'form': form, 'image_form': image, 'error': True})
    else:
        form = SearchForm()
        image = SearchForImageForm()
        return render(request, 'index.html', {'form': form, 'image_form': image, 'error': False})
