import csv
import datetime
import io
import json
import os
import zipfile
from collections import defaultdict

import cv2
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from elasticsearch_dsl import Index, Search, Q
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm, PeopleFilterForm, EditTagForm, FilterSearchForm
from app.models import ImageES, ImageNeo, Tag, Person, Location

from app.processing import getOCR, getExif, dhash, findSimilarImages, upload_images, fs, deleteFolder
from app.processing import frr

from app.utils import add_tag, delete_tag, objectExtractionThreshold, faceRecThreshold, breedsThreshold, \
    is_small, is_medium, is_large, reset_filters, timeHelper
from scripts.esScript import es
from app.nlpFilterSearch import process_query
from app.utils import searchFilterOptions, showDict,faceRecLock
import re
import itertools

from scripts.pathsPC import do


def landingpage(request):
    query = SearchForm()  # query form stays the same
    image = SearchForImageForm()  # fetching image form response
    folders = len(fs.get_all_uris())
    path_form = EditFoldersForm()
    return render(request, "landingpage.html", {'form': query, 'image_form': image, 'folders': folders, 'path_form':path_form})

def update_tags(request, hash):
    new_tags_string = request.POST.get("tags")
    new_tags = re.split('#', new_tags_string)
    new_tags = [tag.strip() for tag in new_tags if tag.strip() != ""]
    image = ImageNeo.nodes.get_or_none(hash=hash)
    old_tags = [x.name for x in image.tag.all()]

    for indx, tag in enumerate(new_tags):
        if tag not in old_tags:
            add_tag(hash, tag)

    for tag in old_tags:
        if tag not in new_tags:
            delete_tag(hash, tag)

    results = {}
    for tag in ImageNeo.nodes.get(hash=hash).tag.all():
        results["#" + tag.name] = tag.image.all()
        count = 0
        for lst_image in results["#" + tag.name]:
            results["#" + tag.name][count] = (lst_image, lst_image.tag.all())
            count += 1
    str_for_query = ""
    for tag in new_tags:
        str_for_query += tag + " "
    return redirect("/results?query=" + str_for_query)

from app.utils import showDict

def index(request):
    # para os filtros
    index_string = "index.html"
    opts = searchFilterOptions
    opts['current_url'] = request.get_full_path()
    filters = FilterSearchForm(initial=opts)

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
            return render(request, index_string,
                          {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})
        else:  # the form filled had a mistake
            results = {}  # blank results dictionary
            for tag in Tag.nodes.all():  # looping through all tag nodes
                results["#" + tag.name] = tag.image.all()  # inserting each tag in the dict w/ all its images as values
                count = 0  # counter
                for lst_image in results["#" + tag.name]:  # for each image of the value of this tag
                    results["#" + tag.name][count] = (lst_image, lst_image.tag.all())  # replace it by a tuple w/ its tags
                    count += 1  # increase counter
            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': True})
    else:
        if 'query' in request.GET:
            query = SearchForm()  # cleaning this form
            image = SearchForImageForm()  # fetching the images form
            query_text = request.GET.get("query")  # fetching the inputted query
            query_array = process_query(query_text)  # processing query with nlp
            tag = "#" + " #".join(query_array)  # arranging tags with '#' before

            """

            result_hashs = list(map(lambda x: x.hash, search(query_array))) # searching and getting result's images hash

            results = {tag: []} # blank results dictionary

            for hash in result_hashs:   # iterating through the result's hashes
                img = ImageNeo.nodes.get_or_none(hash=hash) # fetching the reuslts nodes from DB
                if img is None: # if there is no image with this hash in DB
                    continue    # ignore, advance
                tags = img.tag.all()    # get all tags from the image
                results[tag].append((img, tags))    # insert tags in the dictionary
                img.features = None
            """

            results = get_image_results(query_array)
            print(len(results[tag]))

            if len(query_array) > 0:
                def sort_by_score(elem):
                    image = elem[0]
                    tags = elem[1]
                    score = 0
                    for t in tags: # t -> Tag (NeoNode)
                        for q in query_array:
                            if q in t.name:
                                score += image.tag.relationship(t).score
                                break
                    return - (score / len(query_array))

                results[tag].sort(key=sort_by_score)

            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})

        else:  # first time in the page - no forms filled
            query = SearchForm()
            image = SearchForImageForm()
            results = {}
            for tag in Tag.nodes.all():
                results["#" + tag.name] = tag.image.all()
                count = 0
                for lst_image in results["#" + tag.name]:
                    results["#" + tag.name][count] = (lst_image, lst_image.tag.all())
                    count += 1
            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})

def change_filters(request):
    if request.method != 'POST':
        #print('shouldnt happen!!')
        return redirect('/')

    form = FilterSearchForm(request.POST)
    form.is_valid() # ele diz que o form é invalido se algum
                    # checkbox for False, idk why..
    form = form.cleaned_data

    if 'reset_filters' in request.POST:
        reset_filters()
        return redirect(form['current_url'])

    searchFilterOptions['automatic'] = form['automatic']
    searchFilterOptions['manual'] = form['manual']
    searchFilterOptions['folder_name'] = form['folder_name']
    searchFilterOptions['people'] = form['people']
    searchFilterOptions['text'] = form['text']
    searchFilterOptions['places'] = form['places']
    searchFilterOptions['breeds'] = form['breeds']
    searchFilterOptions['exif'] = form['exif']

    searchFilterOptions['size_large'] = form['size_large']
    searchFilterOptions['size_medium'] = form['size_medium']
    searchFilterOptions['size_small'] = form['size_small']

    searchFilterOptions['insertion_date_activate'] = form['insertion_date_activate']

    time_format_string = '%d-%m-%Y'
    if searchFilterOptions['insertion_date_activate']: # update dates
        try:
            timeHelper['insertion_date_from'] = datetime.datetime.strptime(form['insertion_date_from'], time_format_string)
            searchFilterOptions['insertion_date_from'] = form['insertion_date_from']
        except ValueError: # invalid format
            searchFilterOptions['insertion_date_from'] = None
            timeHelper['insertion_date_from'] = None
        try:
            timeHelper['insertion_date_to'] = datetime.datetime.strptime(form['insertion_date_to'], time_format_string)
            searchFilterOptions['insertion_date_to'] = form['insertion_date_to']
        except ValueError:  # invalid format
            searchFilterOptions['insertion_date_to'] = None
            timeHelper['insertion_date_to'] = None

    searchFilterOptions['taken_date_activate'] = form['taken_date_activate']
    if searchFilterOptions['taken_date_activate']: # update dates
        try:
            timeHelper['taken_date_from'] = datetime.datetime.strptime(form['taken_date_from'], time_format_string)
            searchFilterOptions['taken_date_from'] = form['taken_date_from']
        except ValueError: # invalid format
            searchFilterOptions['taken_date_from'] = None
            timeHelper['taken_date_from'] = None

        try:
            timeHelper['taken_date_to'] = datetime.datetime.strptime(form['taken_date_to'], time_format_string)
            searchFilterOptions['taken_date_to'] = form['taken_date_to']
        except ValueError:  # invalid format
            searchFilterOptions['taken_date_to'] = None
            timeHelper['taken_date_to'] = None

    # -- confiance object extraction --
    max_obj_extr = form['objects_range_max']
    min_obj_extr = form['objects_range_min']

    if min_obj_extr < objectExtractionThreshold * 100:
        min_obj_extr = objectExtractionThreshold * 100
    elif min_obj_extr > 100:
        min_obj_extr = 100

    if max_obj_extr < min_obj_extr:
        max_obj_extr = min_obj_extr
    elif max_obj_extr > 100:
        max_obj_extr = 100

    searchFilterOptions['objects_range_max'] = int(max_obj_extr)
    searchFilterOptions['objects_range_min'] = int(min_obj_extr)
    # -- end confiance object extraction --
    # -- confiance face rec --
    max_face = form['people_range_max']
    min_face = form['people_range_min']

    if min_face < faceRecThreshold * 100:
        min_face = faceRecThreshold * 100
    elif min_face > 100:
        min_face = 100

    if max_face < min_obj_extr:
        max_face = min_obj_extr
    elif max_face > 100:
        max_face = 100

    searchFilterOptions['people_range_max'] = int(max_face)
    searchFilterOptions['people_range_min'] = int(min_face)
    # -- end confiance face rec --


    # -- confiance breeds --
    max_breeds = form['breeds_range_max']
    min_breeds = form['breeds_range_min']

    if min_breeds < breedsThreshold * 100:
        min_breeds = breedsThreshold * 100
    elif min_breeds > 100:
        min_breeds = 100

    if max_breeds < min_breeds:
        max_breeds = min_breeds
    elif max_breeds > 100:
        max_breeds = 100

    searchFilterOptions['breeds_range_max'] = int(max_breeds)
    searchFilterOptions['breeds_range_min'] = int(min_breeds)
    # -- end confiance breeds --


    # -- confiance places --
    max_places = form['places_range_max']
    min_places = form['places_range_min']

    if min_places < breedsThreshold * 100:
        min_places = breedsThreshold * 100
    elif min_places > 100:
        min_places = 100

    if max_places < min_places:
        max_places = min_places
    elif max_places > 100:
        max_places = 100

    searchFilterOptions['places_range_max'] = int(max_places)
    searchFilterOptions['places_range_min'] = int(min_places)
    # -- end confiance places --

    return redirect(form['current_url'])

isBeforeThan = lambda img, filter_ : (img.insertion_date.replace(tzinfo=None) - filter_.replace(tzinfo=None)).days < 0
isLaterThan = lambda img, filter_ : (img.insertion_date.replace(tzinfo=None) - filter_.replace(tzinfo=None)).days > 0

def get_image_results(query_array):
    tag = "#" + " #".join(query_array)  # arranging tags with '#' before

    result_hashs = list(map(lambda x: x.hash, search(query_array)))  # searching and getting result's images hash
    print('len result_hashs : ' , len(result_hashs))
    results = {tag: []}  # blank results dictionary
    for hash in result_hashs:  # iterating through the result's hashes
        remove = set()
        img = ImageNeo.nodes.get_or_none(hash=hash)  # fetching the reuslts nodes from DB
        if img is None:  # if there is no image with this hash in DB
            continue  # ignore, advance


        if not searchFilterOptions['size_small'] and is_small(img.height, img.width):
            continue

        if not searchFilterOptions['size_medium'] and is_medium(img.height, img.width):
            continue

        if not searchFilterOptions['size_large'] and is_large(img.height, img.width):
            continue


        # ---- dates -----
        if searchFilterOptions['insertion_date_activate']:

            fromm = timeHelper['insertion_date_from']
            if fromm is not None and isBeforeThan(img, fromm):
                    continue # is before the limit, not shown
            too = timeHelper['insertion_date_to']
            if too is not None and isLaterThan(img, too):
                    continue

        """
            fromm = timeHelper['insertion_date_from']
            if fromm is not None:
                if isBeforeThan(img, fromm):
                    continue # is before the limit, not shown
            too = timeHelper['insertion_date_to']
            if too is not None:
                if isLaterThan(img, too):
                    continue
                    """

        #       ---- people ---

        people = img.person.all()
        # verifica se a query ta dentro do nome
        dentro = any([q in p.name.lower() for q in query_array for p in people])
        if dentro:
            if not searchFilterOptions['people']:
                remove.add(True)
            else:
                people = img.person.all()
                relationships = [img.person.all_relationships(t) for t in people if not set(t.name.lower().split(' ')).isdisjoint(query_array)]
                relationships = [rel for r in relationships for rel in r]
                #print('len rels', len(relationships))
                # if len(relationships) > 0:
                minn = searchFilterOptions['people_range_min']
                maxx = searchFilterOptions['people_range_max']
                outside_limits = all([rel.confiance * 100 < minn or rel.confiance * 100 > maxx for rel in relationships])
                #print([rel.confiance for rel in relationships])
                remove.add(outside_limits)


        # -- manual --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='manual')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
                remove.add(not searchFilterOptions['manual'])

        # -- object --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='object')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            if not searchFilterOptions['automatic']:
                remove.add(True)
            else:
                tags = [t for t in img.tag.match(originalTagSource='object')]
                relationships = [img.tag.all_relationships(t) for t in tags if not set(t.name.lower().split(' ')).isdisjoint(query_array)]
                relationships = [ rel for r in relationships for rel in r]
                # if len(relationships) > 0:
                minn = searchFilterOptions['objects_range_min']
                maxx = searchFilterOptions['objects_range_max']
                outside_limits = all([rel.score*100 < minn or rel.score*100 > maxx for rel in relationships])
                #print([rel.score for rel in relationships])
                remove.add(outside_limits) # adiciona Falso se n houver nenhum

        # -- folder name --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='folder')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            remove.add(not searchFilterOptions['folder_name'])


        # -- ocr --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='ocr')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            remove.add(not searchFilterOptions['text'])

        # -- exif --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='exif')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            remove.add(not searchFilterOptions['exif'])

        # -- places --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='places')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            if not searchFilterOptions['breeds']:
                remove.add(True)
            else:
                tags = [t for t in img.tag.match(originalTagSource='places')]
                relationships = [img.tag.all_relationships(t) for t in tags if not set(t.name.lower().split(' ')).isdisjoint(query_array)]
                relationships = [rel for r in relationships for rel in r]
                #if len(relationships) > 0:
                minn = searchFilterOptions['places_range_min']
                maxx = searchFilterOptions['places_range_max']
                outside_limits = all([rel.score * 100 < minn or rel.score * 100 > maxx for rel in relationships])
                remove.add(outside_limits)

        # -- breeds --
        tags = [t.name.lower() for t in img.tag.match(originalTagSource='breeds')]
        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            #print('dentro breeds')
            if not searchFilterOptions['breeds']:
                remove.add(True)
            else:
                tags = [t for t in img.tag.match(originalTagSource='breeds')]
                relationships = [img.tag.all_relationships(t) for t in tags if not set(t.name.lower().split(' ')).isdisjoint(query_array)]
                relationships = [rel for r in relationships for rel in r]
                #if len(relationships) > 0:
                minn = searchFilterOptions['breeds_range_min']
                maxx = searchFilterOptions['breeds_range_max']
                outside_limits = all([rel.score * 100 < minn or rel.score * 100 > maxx for rel in relationships])
                #print('breeds', [rel.score for rel in relationships])
                remove.add(outside_limits)


        #print('remove', remove)
        if not all(remove):
            #print('adicionou..')
            img.features = None
            results[tag].append((img, img.tag.all()))  # insert tags in the dictionary
    return results

def delete(request, path):
    form = SearchForm()
    image = SearchForImageForm()
    pathf = EditFoldersForm()
    do(deleteFolder, path)
    folders = fs.get_all_uris()
    return render(request, 'managefolders.html',
                  {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})

def managefolders(request):
    if 'path' in request.GET:
        upload_images(request.GET.get('path'))
        '''
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
        '''
        response = redirect('/folders')
        return response
    else:
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.get_all_uris()
        return render(request, 'managefolders.html',
                      {'form': form, 'image_form': image, 'folders': folders, 'path_form': pathf})

people_url_string = '/people'
def managepeople(request):

    if request.method == 'POST':
        filters = PeopleFilterForm(request.POST)
        filters.is_valid()
        filters2 = filters.cleaned_data

        showDict['unverified'] = filters2['unverified']
        showDict['verified'] = filters2['verified']

        return redirect(people_url_string)

    form = SearchForm()
    image = SearchForImageForm()
    names = PersonsForm()
    filters = PeopleFilterForm(initial=showDict)
    return render(request, 'renaming.html',
                  {'form': form, 'image_form': image, 'names_form': names, 'filters': filters})

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
    upload_images(data["path"])
    return redirect('/folders')

def searchtag(request):
    get = [request.GET.get('tag')]
    q = Q('bool', should=[Q('term', tags=tag) for tag in get], minimum_should_match=1)
    s = Search(using=es, index='image').query(q)
    execute = s.execute()
    return render(request, 'index.html')

def update_folders(request):
    folders = fs.get_all_uris()
    for folder in folders:
        upload_images(folder)
    return HttpResponseRedirect(reverse('managefolders'))

def update_faces(request):
    if request.method != 'POST':
        redirect(people_url_string)

    form = PersonsForm(request.POST)
    if not form.is_valid():
        print('invalid form!!!')

    #print(form.cleaned_data)
    data = form.cleaned_data

    imgs = int(len(form.cleaned_data) / 5)
    for i in range(imgs):
        # if not data['person_verified_%s' % str(i)]:
        #    continue
        thumbname = data['person_image_%s' % str(i)]
        new_personname = data['person_name_%s' % str(i)]

        # retirar isto abaixo dps!!!
        #new_personname = new_personname.split(' ')[0]
        old_personname = data['person_before_%s' % str(i)]
        verified = True
        if not data['person_verified_%s' % str(i)]:
            # continue
            new_personname = old_personname
            verified = False

        # if old_personname != new_personname:
        image_hash = data['person_image_id_%s' % str(i)]
        try:
            faceRecLock.acquire()
            frr.change_relationship(image_hash, new_personname, old_personname, thumbnail=thumbname, approved=verified)
            if old_personname != new_personname:
                frr.change_name_tag_es(image_hash, new_personname, old_personname)
        finally:
            faceRecLock.release()
    try:
        faceRecLock.acquire()
        frr.update_data()
    finally:
        faceRecLock.release()

    if 'reload' in request.POST:
        #print('reload was called')
        try:
            faceRecLock.acquire()
            frr.reload()
        finally:
            faceRecLock.release()

    return redirect(people_url_string)

def dashboard(request):
    form = SearchForm()
    image = SearchForImageForm()
    person_number = 0
    for _ in Person.nodes.all():
        person_number += 1

    location_number = 0
    for _ in Location.nodes.all():
        location_number +=1

    results = {}
    counts = {}
    for tag in Tag.nodes.all():

        results["#" + tag.name] = tag.image.all()
        count = 0
        for lst_image in results["#" + tag.name]:
            results["#" + tag.name][count] = (lst_image, lst_image.tag.all())
            count += 1
        counts[tag.name] = len(results["#" + tag.name])

    count_tags = dict(sorted(counts.items(), key=lambda item: item[1],
                            reverse=True))  # sort the dict by its value (count), from the greatest to the lowest
    if len(count_tags) < 10:
        count_tags = dict(itertools.islice(count_tags.items(), len(count_tags)))
    else:
        count_tags = dict(itertools.islice(count_tags.items(), 10))  # only want the first top 10 more common tags
    count_tags = json.dumps(count_tags)

    ## original tag source statistics
    count_original_tag_source = {}
    all_tag_labels = {"ocr": "text", "manual": "manual", "object": "objects", "places": "places",
                    "exif": "image properties", "folder": "folder's name", "breeds": "breed"}
    for tag in Tag.nodes.all():
        img_list = tag.image.all()
        for img in img_list:
            rel = img.tag.relationship(tag)
            original_tag_source = rel.originalTagSource
            original_tag_source = all_tag_labels[original_tag_source]
            # print(tag.name, original_tag_source)
            if original_tag_source not in count_original_tag_source:
                count_original_tag_source[original_tag_source] = 1
            else:
                count_original_tag_source[original_tag_source] += 1

    # print(count_original_tag_source)
    for label in all_tag_labels.values():
        if label not in count_original_tag_source.keys():
            count_original_tag_source[label] = 0

    count_original_tag_source = dict(sorted(count_original_tag_source.items(), key=lambda item: item[1]))
    #print(count_original_tag_source)
    return render(request, 'dashboard.html',
                  {'form': form, 'image_form': image, 'results': results, 'counts': count_tags,
                   'countTagSource': count_original_tag_source, 'numbers': {'person': person_number, 'location': location_number}})

def calendar_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    dates_insertion = {}
    dates_creation = {}
    previous_images = []
    for tag in Tag.nodes.all():
        img_list = tag.image.all()
        for img in img_list:
            if img not in previous_images:
                insertion_date = str(img.insertion_date)
                creation_date = str(img.creation_date)
                insertion_date = insertion_date.split(" ")[0]
                creation_date = creation_date.split(" ")[0]
                if insertion_date not in dates_insertion:
                    dates_insertion[insertion_date] = 1
                else:
                    dates_insertion[insertion_date] += 1
                if creation_date != "None":
                    if creation_date not in dates_creation:
                        dates_creation[creation_date] = 1
                    else:
                        dates_creation[creation_date] += 1

                previous_images += [img]

            else:
                continue

    dates_insertion = dict(sorted(dates_insertion.items(), key=lambda item: item[0]))
    dates_insertion = json.dumps(dates_insertion)
    dates_creation = dict(sorted(dates_creation.items(), key=lambda item: item[0]))
    dates_creation = json.dumps(dates_creation)
    return render(request, 'gallery.html',
                  {'form': form, 'image_form': image, 'dates_insertion': dates_insertion, 'dates_creation': dates_creation})

def objects_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_object_tags = {}
    for tag in Tag.nodes.all():
        img_list = tag.image.all()
        for img in img_list:
            rel = img.tag.relationship(tag)
            original_tag_source = rel.originalTagSource
            if original_tag_source == "object":
                first_letter = tag.name[0].upper()
                if first_letter not in all_object_tags.keys():
                    all_object_tags[first_letter] = [tag.name.lower()]
                else:
                    if tag.name not in all_object_tags[first_letter]:
                        all_object_tags[first_letter] += [tag.name.lower()]

    for key in all_object_tags:
        value = all_object_tags[key]
        value = value.sort()

    all_object_tags = dict(sorted(all_object_tags.items()))

    return render(request, 'objectsGallery.html',
                  {'form': form, 'image_form': image, 'objectTags': all_object_tags})

def people_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_names = Person().getVerified()

    all_names = sorted(list(set(all_names)))

    print(all_names)

    all_names_dict = {}

    for name in all_names:
        first_letter = name[0]
        if first_letter not in all_names_dict.keys():
            all_names_dict[first_letter] = [name]
        else:
            all_names_dict[first_letter] += [name]
    print(all_names_dict)
    return render(request, 'peopleGallery.html',
                  {'form': form, 'image_form': image, 'people': all_names_dict})

def scenes_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_place_tags = {}
    for tag in Tag.nodes.all():
        img_list = tag.image.all()
        for img in img_list:
            rel = img.tag.relationship(tag)
            original_tag_source = rel.originalTagSource
            if original_tag_source == "places":
                first_letter = tag.name[0].upper()
                if first_letter not in all_place_tags.keys():
                    all_place_tags[first_letter] = [tag.name.lower()]
                else:
                    if tag.name not in all_place_tags[first_letter]:
                        all_place_tags[first_letter] += [tag.name.lower()]

    for key in all_place_tags:
        value = all_place_tags[key]
        value = value.sort()

    all_place_tags = dict(sorted(all_place_tags.items()))
    return render(request, 'placesGallery.html',
                  {'form': form, 'image_form': image, 'placesTags': all_place_tags})

def text_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_text_tags = {}
    for tag in Tag.nodes.all():
        img_list = tag.image.all()
        for img in img_list:
            rel = img.tag.relationship(tag)
            original_tag_source = rel.originalTagSource
            if original_tag_source == "ocr":
                first_letter = tag.name[0].upper()
                if first_letter not in all_text_tags.keys():
                    all_text_tags[first_letter] = [tag.name.lower()]
                else:
                    if tag.name not in all_text_tags[first_letter]:
                        all_text_tags[first_letter] += [tag.name.lower()]

    for key in all_text_tags:
        value = all_text_tags[key]
        value = value.sort()

    all_text_tags = dict(sorted(all_text_tags.items()))

    return render(request, 'textGallery.html',
                  {'form': form, 'image_form': image, 'textTags': all_text_tags})

def export_to_zip(request, ids):
    ids = ids[1:]
    if ids.strip() == '':
        return HttpResponse(content_type='text/json')

    ids = ids.split("&")
    # Create zip
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')
    for id in ids:
        img = ImageNeo.nodes.get_or_none(hash=id)
        if not img: continue

        path = os.path.join(img.folder_uri, img.name)
        zip_file.writestr(re.split("[\\\/]+", path)[-1],
                          open(path, 'rb').read())
    zip_file.close()
    # Return zip
    response = HttpResponse(buffer.getvalue())
    response['Content-Type'] = 'application/x-zip-compressed'
    response['Content-Disposition'] = 'attachment; filename=images.zip'
    return response

def export_to_excel(request, ids):
    ids = ids[1:]
    if ids.strip() == '':
        return HttpResponse(content_type='text/json')

    ids = ids.split("&")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="images.csv"'

    csv_file = csv.writer(response)
    csv_file.writerow(['uri', 'creation time', 'insertion time', 'format', 'width', 'height', 'tags', 'persons', 'locations'])

    for id in ids:
        img = ImageNeo.nodes.get_or_none(hash=id)
        if not img: continue

        uri = os.path.join(img.folder_uri, img.name)
        creation_time = img.creation_date
        insertion_date = img.insertion_date
        img_format = img.format
        width = img.width
        height = img.height
        tags = [t.name for t in img.tag]
        persons = [p.name for p in img.person]
        locations = []
        for l in img.location:
            locations.append(l.name)
            for city in l.city:
                locations.append(city.name)
                for region in city.region:
                    locations.append(region.name)
                    for country in region.country:
                        locations.append(country.name)

        csv_file.writerow([uri, creation_time, insertion_date, img_format, width,
                           height, tags, persons, locations])

    return response
  
def locationsGallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    locations = {}
    for tag in Tag.nodes.all():
        imgList = tag.image.all()
        for img in imgList:
            location = img.location
            if location not in locations:
                locations[location] = 1
            else:
                locations[location] += 1
            #print(location)
    return render(request, 'locationsGallery.html',
                  {'form': form, 'image_form': image, 'locations': locations})
