from django.shortcuts import render
from app.forms import SearchForm

def index(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            query_array = form.cleaned_data['query'].split(" ")
            return render(request, "index.html", {'form': form})
    else:
        form = SearchForm()
        return render(request, 'index.html', {'form': form})
