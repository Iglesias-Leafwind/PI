import json
import os
import re

import cv2
from django.shortcuts import render
from elasticsearch_dsl import Index, Search, Q
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm
from app.models import ImageES, ImageNeo, Tag, Person
from app.processing import getOCR, getExif, dhash, findSimilarImages, uploadImages, fs, deleteFolder
from manage import es
from app.nlpFilterSearch import processQuery


def index(request):
    if request.method == 'POST':  # if it's a POST, we know it's from search by image
        query = SearchForm()  # query form stays the same
        image = SearchForImageForm(request.POST, request.FILES)  # fetching image form response

        if image.is_valid() and image.cleaned_data["image"]:  # if search by image is valid
            imagepath = image.cleaned_data["image"]  # get inserted path
            image_array = findSimilarImages(imagepath)  # find similar images
            results = {"results": []}  # blank results dictionary
            for i in image_array:  # looping through the results of the search
                getresult = ImageNeo.nodes.get_or_none(hash=i)  # fetching each corresponding node
                if getresult:  # if it exists
                    results["results"].append((getresult, getresult.tag.all()))  # append the node and its tags
            return render(request, "index.html", {'form': query, 'image_form': image, 'results': results, 'error': False})
        else:  # the form filled had a mistake
            results = {}  # blank results dictionary
            for tag in Tag.nodes.all():  # looping through all tag nodes
                results["#" + tag.name] = tag.image.all()  # inserting each tag in the dict w/ all its images as values
                count = 0  # counter
                for lstImage in results["#" + tag.name]:  # for each image of the value of this tag
                    results["#" + tag.name][count] = (lstImage, lstImage.tag.all())  # replace it by a tuple w/ its tags
                    count += 1  # increase counter
            return render(request, 'index.html', {'form': query, 'image_form': image, 'results': results, 'error': True})
    else:
        if 'query' in request.GET:
            query = SearchForm()    # cleaning this form
            image = SearchForImageForm()    # fetching the images form

            query_text = request.GET.get("query")   # fetching the inputted query
            query_array = processQuery(query_text)  # processing query with nlp
            tag = "#" + " #".join(query_array)  # arranging tags with '#' before

            result_hashs = list(map(lambda x: x.hash, search(query_array))) # searching and getting result's images hash
            results = {tag: []} # blank results dictionary
            for hash in result_hashs:   # iterating through the result's hashes
                img = ImageNeo.nodes.get_or_none(hash=hash) # fetching the reuslts nodes from DB
                if img is None: # if there is no image with this hash in DB
                    continue    # ignore, advance
                tags = img.tag.all()    # get all tags from the image
                results[tag].append((img, tags))    # insert tags in the dictionary

            return render(request, "index.html", {'form': query, 'image_form': image, 'results': results, 'error': False})

        else:  # first time in the page - no forms filled
            query = SearchForm()
            image = SearchForImageForm()

            results = {}
            for tag in Tag.nodes.all():
                results["#" + tag.name] = tag.image.all()
                count = 0
                for lstImage in results["#" + tag.name]:
                    results["#" + tag.name][count] = (lstImage, lstImage.tag.all())
                    count += 1
            return render(request, 'index.html', {'form': query, 'image_form': image, 'results': results, 'error': False})

def delete(request, path):
    form = SearchForm()
    image = SearchForImageForm()
    pathf = EditFoldersForm()
    deleteFolder(path)
    folders = fs.getAllUris()
    folders = [ (f, re.sub("\\\\+|/+|:+", "", f)) for f in folders]
    return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})


def managefolders(request):
    if 'path' in request.GET:
        uploadImages(request.GET.get('path'))
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
        folders = [ (f, re.sub("\\\\+|/+|:+", "", f)) for f in folders]
        return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})
    else:
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
        folders = [ (f, re.sub("\\\\+|/+|:+", "", f)) for f in folders]
        return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})


def managepeople(request):
    if request.method == 'POST':
        form = SearchForm()
        image = SearchForImageForm()
        names = PersonsForm(request.POST)
        if names.is_valid() and names.has_changed():  # if names changed
            i = 0
            for field in names.declared_fields:
                if field.has_changed:
                    fimage = names.cleaned_data["person_image_" + str(i)]
                    fname = names.cleaned_data["person_name_" + str(i)]
                    profile = Person.objects.get(icon=fimage)
                    profile.name = fname
                    profile.save()
                    names = PersonsForm()
        return render(request, 'renaming.html', {'form': form, 'image_form': image, 'names_form': names})
    else:
        form = SearchForm()
        image = SearchForImageForm()
        names = PersonsForm()
        return render(request, 'renaming.html', {'form': form, 'image_form': image, 'names_form': names})



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


def search(tags):
    q = Q('bool', should=[Q('term', tags=tag) for tag in tags], minimum_should_match=1)
    s = Search(using=es, index='image').query(q)
    return s.execute()


def alreadyProcessed(img_path):
    image = cv2.imread(img_path)
    hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=hash)

    return True if existed else False


def upload(request):
    data = json.loads(request.body)
    uploadImages(data["path"])
    return render(request, 'index.html')


def searchtag(request):
    get = [request.GET.get('tag')]
    q = Q('bool', should=[Q('term', tags=tag) for tag in get], minimum_should_match=1)
    s = Search(using=es, index='image').query(q)
    execute = s.execute()
    for i in execute:
        print(i)
    return render(request, 'index.html')