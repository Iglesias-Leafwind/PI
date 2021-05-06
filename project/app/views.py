import json

import cv2
from django.shortcuts import render
from elasticsearch_dsl import Index, Search, Q
from django import forms
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm
from app.models import ImageES, ImageNeo
from app.processing import getOCR, getExif, dhash
from manage import es


def index(request):
    folders = ["pasta/pasta1", "desktop/", "transferencias/"]  # folders should be Folder.objects.all()

    if request.method == 'POST':
        query = SearchForm(request.POST)
        image = SearchForImageForm(request.POST, request.FILES)
        pathf = EditFoldersForm(request.POST)
        names = PersonsForm(request.POST)

        fileset = ['opcao 1', 'opcao 2', 'opcao 3']  # fileset = NomedoFicheiro.cenas()
        pathf.fields['path'] = forms.ChoiceField(
            widget=forms.Select(choices=tuple([(choice, choice) for choice in fileset])))

        if query.is_valid() and not query.cleaned_data['query'] == '':  # search bar input was valid and not null
            query_array = query.cleaned_data['query']
            # use the query_array to search by tags and pass them as 'results'
            query = SearchForm()
            return render(request, "index.html",
                          {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders,
                           'names_form': names,
                           'results': {'#querytag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                       '#querytag2': ['isto é uma segunda imagem',
                                                      'isto é outra ultima imagem']}})  # return new index with results this time and cleaned form
        elif image.is_valid() and image.cleaned_data["image"]:  # if search by image file exists
            image = image.cleaned_data["image"]
            # use the image to process image and look for similar images in model
            image = SearchForImageForm()
            return render(request, "index.html",
                          {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders,
                           'names_form': names,
                           'results': {'#imagetag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                       '#imagetag2': ['isto é uma segunda imagem',
                                                      'isto é outra ultima imagem']}})  # return new index with results this time and cleaned form
        elif pathf.is_valid() and pathf.cleaned_data["path"]:  # if path of new folder has a name, then it exists
            # new = Folder(url = pathf.path)
            # new.save()
            pathf = EditFoldersForm()
            return render(request, "index.html",
                          {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders,
                           'names_form': names,
                           'results': {'#folderstag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                       '#folderstag2': ['isto é uma segunda imagem',
                                                        'isto é outra ultima imagem']}})  # return new index with results this time and cleaned form
        elif names.is_valid() and names.has_changed():  # if names changed
            i = 0
            for field in names.declared_fields:
                if field.has_changed:
                    fimage = names.cleaned_data["person_image_" + str(i)]
                    fname = names.cleaned_data["person_name_" + str(i)]
                    # profile = Person.objects.get(icon=fimage)
                    # profile.name = fname
                    # profile.save()
            names = PersonsForm()
            return render(request, "index.html",
                          {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders,
                           'names_form': names,
                           'results': {'#namestag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                       '#namestag2': ['isto é uma segunda imagem',
                                                      'isto é outra ultima imagem']}})  # return new index with results this time and cleaned form

        else:  # the form filled had a mistake
            form = SearchForm()
            image = SearchForImageForm()
            pathf = EditFoldersForm()
            names = PersonsForm()
            return render(request, 'index.html',
                          {'form': form, 'image_form': image, 'path_form': pathf, 'folders': folders,
                           'names_form': names,
                           'results': {'#errortag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                       '#errortag2': ['isto é uma segunda imagem', 'isto é outra ultima imagem']}})
    else:  # first time in the page - no forms filled
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        names = PersonsForm()

        fileset = ['opcao 1', 'opcao 2', 'opcao 3']  # fileset = NomedoFicheiro.cenas()
        pathf.fields['path'] = forms.CharField(label="New Path:", widget=forms.Select(
            choices=tuple([(choice, choice) for choice in fileset])))

        return render(request, 'index.html',
                      {'form': form, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names,
                       'results': {'#indextag1': ['isto é uma imagem', 'isto é outra', 'cenas', 'e mais cenas'],
                                   '#indextag2': ['isto é uma segunda imagem', 'isto é outra ultima imagem']}})


# OCR
def ocr(request):
    get = request.GET.get("path")
    res = getOCR(get)
    return render(request, 'ocr.html', {'res': res})


# EXIF
def exif(request):
    get = request.GET.get("path")
    res = getExif(get)
    isProcessed = alreadyProcessed(get)
    if not isProcessed:
        imgread = cv2.imread(get)
        hash = dhash(imgread)
        img = ImageNeo(folder_uri=get, name="something", hash=hash)
        img.save()
    return render(request, 'exif.html', {'res': res, 'isProcessed': isProcessed})


# Elasticsearch
def createIndex(request):
    uri = request.GET.get("uri")
    tag = request.GET.get("tag")

    i = Index(using=es, name=request.GET.get("index"))
    if not i.exists(using=es):
       i.create()

    ImageES(meta={'id': uri}, uri=uri, tags=[tag]).save(using=es)

    return render(request, 'insert_es.html')

def search(request):
    tags = request.GET.get("tags")
    q = Q('bool', should=[Q('term', tags=tag) for tag in tags],
          minimum_should_match=1)

    s = Search(using=es, index='image').query(q)
    r = s.execute()
    for hit in r:
        print("score: %s, uri: %s, tags: %s" % (hit.meta.score, hit.uri, hit.tags))

    return render(request, 'es.html', {'r': r})


def alreadyProcessed(img_path):
    image = cv2.imread(img_path)
    hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=hash)

    return True if existed else False

def findSimilar(request):
    get = request.GET.get("path")
    findSimilarImages(get)
    return render(request, 'index.html')
