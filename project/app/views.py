import json
import os
import re

import cv2
from django.shortcuts import render
from elasticsearch_dsl import Index, Search, Q
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm
from app.models import ImageES, ImageNeo, Tag
from app.processing import getOCR, getExif, dhash, findSimilarImages, uploadImages, fs, deleteFolder
from manage import es
from app.nlpFilterSearch import processQuery

def index(request):
    fileset = None
    folders = fs.getAllUris()

    if request.method == 'POST':
        query = SearchForm(request.POST)
        image = SearchForImageForm(request.POST, request.FILES)
        pathf = EditFoldersForm(request.POST)
        names = PersonsForm(request.POST)

        if image.is_valid() and image.cleaned_data["image"]:  # if search by image file exists
            imagepath = image.cleaned_data["image"]
            image_array = findSimilarImages(imagepath)
            results = {"results": []}
            for i in image_array:
                getresult = ImageNeo.nodes.get_or_none(hash=i)
                if getresult:
                    results["results"].append((getresult, getresult.tag.all()))
            image = SearchForImageForm()


            return render(request, "index.html", {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names, 'results': results})  # return new index with results this time and cleaned form
        elif pathf.is_valid() and pathf.cleaned_data["path"]:  # if path of new folder has a name, then it exists
            uploadImages(pathf.cleaned_data["path"])
            pathf = EditFoldersForm()
            folders = fs.getAllUris()
            results = {}
            for tag in Tag.nodes.all():
                results["#" + tag.name] = tag.image.all()
                count = 0
                for lstImage in results["#" + tag.name]:
                    results["#" + tag.name][count] = (lstImage, lstImage.tag.all())
                    count += 1
            return render(request, "index.html", {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names, 'results': results})  # return new index with results this time and cleaned form
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

            results = {}
            for tag in Tag.nodes.all():
                results["#" + tag.name] = tag.image.all()

            return render(request, "index.html", {'form': query, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names, 'results': results})  # return new index with results this time and cleaned form

        else:  # the form filled had a mistake
            form = SearchForm()
            image = SearchForImageForm()
            pathf = EditFoldersForm()
            names = PersonsForm()

            results = {}
            for tag in Tag.nodes.all():
                results["#" + tag.name] = tag.image.all()
                count = 0
                for lstImage in results["#" + tag.name]:
                    results["#" + tag.name][count] = (lstImage, lstImage.tag.all())
                    count += 1
            return render(request, 'index.html', {'form': form, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names, 'results': results})

    elif request.method == 'GET' and 'query' in request.GET:
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        names = PersonsForm()

        query_text = request.GET.get("query")
        query_array = processQuery(query_text)
        tag = "#" + " #".join(query_array)

        result_hashs = list(map(lambda x: x.hash, search(query_array)))
        results = {tag: []}
        for hash in result_hashs:
            img = ImageNeo.nodes.get_or_none(hash=hash)
            if img is None:
                continue

            tags = img.tag.all()
            results[tag].append((img, tags))

        return render(request, "index.html", {'form': form, 'image_form': image, 'path_form': pathf, 'folders': folders, 'names_form': names, 'results': results})  # return new index with results this time and cleaned form

    else:  # first time in the page - no forms filled
        form = SearchForm()
        image = SearchForImageForm()
        names = PersonsForm()
        pathf = EditFoldersForm()

        results={}
        for tag in Tag.nodes.all():
            results["#" + tag.name] = tag.image.all()
            count = 0
            for lstImage in results["#" + tag.name]:
                results["#" + tag.name][count] = (lstImage, lstImage.tag.all())
                count += 1
        return render(request, 'index.html', {'form': form, 'path_form': pathf, 'image_form': image, 'folders': folders, 'names_form': names, 'results': results})


#def getFileSet(fileset):
#    if not fileset:
#        fileset = future.result()
#    return fileset


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


def delete(request):
    deleteFolder(request.GET.get("path"))
    return render(request, 'managefolders.html')


def managefolders(request):
    form = SearchForm()
    folders = fs.getAllUris()
    pathf = EditFoldersForm()
    return render(request, 'managefolders.html', {'form': form, 'folders': folders, 'path_form': pathf})