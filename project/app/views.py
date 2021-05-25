import json
import os
import re
from collections import defaultdict

import cv2
from django.shortcuts import render, redirect
from elasticsearch_dsl import Index, Search, Q
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm, EditTagForm
from app.models import ImageES, ImageNeo, Tag, Person
from app.processing import getOCR, getExif, dhash, findSimilarImages, uploadImages, fs, deleteFolder, frr
from app.utils import addTag, deleteTag
from manage import es
from app.nlpFilterSearch import processQuery
import re

def updateTags(request, hash):
    newTagsString = request.POST.get("tagsTextarea")
    newTags = re.split('\s|\s+|\t|#', newTagsString)
    newTags = [tag for tag in newTags if tag != ""]
    print(newTags)
    image = ImageNeo.nodes.get_or_none(hash=hash)
    oldTags = [x.name for x in image.tag.all()]
    print(oldTags)
    for tag in newTags:
        if tag not in oldTags:
            addTag(hash, tag)

    for tag in oldTags:
        if tag not in newTags:
            deleteTag(hash, tag)

    query = SearchForm()
    image = SearchForImageForm()
    results = {}
    for tag in Tag.nodes.all():
        results["#" + tag.name] = tag.image.all()
        count = 0
        for lstImage in results["#" + tag.name]:
            results["#" + tag.name][count] = (lstImage, lstImage.tag.all())
            count += 1

    return render(request, "index.html", {'form': query, 'image_form': image, 'results': results, 'error': False})


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
    return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})


def managefolders(request):
    if 'path' in request.GET:
        uploadImages(request.GET.get('path'))
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
        return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})
    else:
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
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

def updateFolders(request):
    folders = fs.getAllUris()
    for folder in folders:
        uploadImages(folder)
    form = SearchForm()
    image = SearchForImageForm()
    pathf = EditFoldersForm()
    return render(request, 'managefolders.html', {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})

def update_faces(request):
    if request.method != 'POST':
        print('method not post!!!')
        pass

    form = PersonsForm(request.POST)
    if not form.is_valid():
        print('invalid form!!!')
        # return or smth
    print(form.cleaned_data)
    data = form.cleaned_data

    imgs = int(len(form.cleaned_data) / 5)
    listt = []
    for i in range(imgs):
        if not data['person_verified_%s' % str(i)]:
            continue
        thumbname = data['person_image_%s' % str(i)]
        new_personname = data['person_name_%s' % str(i)]

        # retirar isto abaixo dps!!!
        new_personname = new_personname.split(' ')[0]
        old_personname = data['person_before_%s' % str(i)]

        #if old_personname == new_personname:
        #    continue

        image_hash = data['person_image_id_%s' % str(i)]
        image = ImageNeo.nodes.get_or_none(hash=image_hash)
        if image is None:
            print('IMAGE IS NONE')

        new_person = Person.nodes.get_or_none(name=new_personname)
        if new_person is None:
            new_person = Person(name=new_personname, icon=thumbname).save()
            print('new person was created')

        old_person = Person.nodes.get_or_none(name=old_personname)
        if old_person is None:
            print('OLD PERSON IS NONE')

        changeRelationship(image, new_person, old_person)

    frr.update_data()

    form = SearchForm()
    image = SearchForImageForm()
    names = PersonsForm()
    return render(request, 'renaming.html', {'form': form, 'image_form': image, 'names_form': names})

def changeRelationship(img, new_person, old_person):
    # all_rels = [(person.image.relationship(img), person, img) for person in people for img in person.image.all()]

    existent_rel = old_person.image.relationship(img)
    """
    coordinates = ArrayProperty()
    encodings = ArrayProperty()
    icon = StringProperty()
    confiance = FloatProperty()
    approved = BooleanProperty()
    """
    relinfo = {
        'coordinates' : existent_rel.coordinates,
        'encodings' : existent_rel.encodings,
        'icon' : existent_rel.icon,
        'confiance' : 1.0,
        'approved' : True
    }

    # nao vai resultar se tiver + do q 1 relacao... mau TODO melhorar
    old_person.image.disconnect(img)
    img.person.connect(new_person, relinfo)



