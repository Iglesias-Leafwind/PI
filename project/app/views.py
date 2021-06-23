## @package app
#  This module contains functions that will be called by django urls
#   Meaning that these functions are what each endpoint will do
#  More details.
import csv
import datetime
import io
import json
import os
import zipfile

import cv2
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from elasticsearch_dsl import Index, Search, Q
from app.forms import SearchForm, SearchForImageForm, EditFoldersForm, PersonsForm, PeopleFilterForm, EditTagForm, FilterSearchForm
from app.models import ImageES, ImageNeo, Tag, Person, Location, Folder

from app.processing import get_ocr, get_exif, dhash, find_similar_images, upload_images, fs, delete_folder, \
    get_all_images_of_folder, frr

from app.utils import add_tag, delete_tag, objectExtractionThreshold, faceRecThreshold, breedsThreshold, \
    is_small, is_medium, is_large, reset_filters, timeHelper, placesThreshold
from scripts.esScript import es
from app.nlpFilterSearch import process_query, process_text
from app.utils import searchFilterOptions, showDict,faceRecLock
import re
import itertools
import logging
from scripts.pathsPC import do


## First page that the users will find themselves in when opening our app
#
#  More details.
def landingpage(request):
    query = SearchForm()  # query form stays the same
    image = SearchForImageForm()  # fetching image form response
    folders = len(fs.get_all_uris())
    path_form = EditFoldersForm()
    return render(request, "landingpage.html", {'form': query, 'image_form': image, 'folders': folders, 'path_form':path_form})

## Request where tags get updated of a specific image
#
#  More details.
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

    str_for_query = ""
    for tag in new_tags:
        str_for_query += tag + " "
    return redirect("/results?query=" + str_for_query)

from app.utils import showDict

index_string = "index.html"

## Index page is the search results page
#
#  More details.
def index(request):
    # para os filtros
    opts = searchFilterOptions
    opts['current_url'] = request.get_full_path()
    filters = FilterSearchForm(initial=opts)

    if request.method == 'POST':  # if it's a POST, we know it's from search by image
        query = SearchForm()  # query form stays the same
        image = SearchForImageForm(request.POST, request.FILES)  # fetching image form response

        if image.is_valid() and image.cleaned_data["image"]:  # if search by image is valid
            results = search_by_image_page_resources(image)
            return render(request, index_string,
                          {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})
        else:  # the form filled had a mistake
            results = error_in_form_showing_all_images()
            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': True})
    else:
        if 'query' in request.GET:
            image, query, results = query_search_page_resources(request)
            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})

        else:  # first time in the page - no forms filled
            image, query, results = first_time_in_page_resources()
            return render(request, index_string, {'filters_form' : filters, 'form': query, 'image_form': image, 'results': results, 'error': False})

## Function to create forms for the first time in a page
#
#  More details.
def first_time_in_page_resources():
    query = SearchForm()
    image = SearchForImageForm()
    results = {}
    for tag in Tag.nodes.all():
        results["#" + tag.name] = tag.image.all()
        count = 0
        for lst_image in results["#" + tag.name]:
            results["#" + tag.name][count] = (lst_image, lst_image.tag.all())
            count += 1
    return image, query, results

## When an error occurs in a form this function is called and it shows all images
#
#  More details.
def error_in_form_showing_all_images():
    results = {}  # blank results dictionary
    for tag in Tag.nodes.all():  # looping through all tag nodes
        results["#" + tag.name] = tag.image.all()  # inserting each tag in the dict w/ all its images as values
        count = 0  # counter
        for lst_image in results["#" + tag.name]:  # for each image of the value of this tag
            results["#" + tag.name][count] = (lst_image, lst_image.tag.all())  # replace it by a tuple w/ its tags
            count += 1  # increase counter
    return results

## Searching by image
#
#  More details.
def search_by_image_page_resources(image):
    imagepath = image.cleaned_data["image"]  # get inserted path
    image_array = find_similar_images(imagepath)  # find similar images
    results = {"results": []}  # blank results dictionary
    for i in image_array:  # looping through the results of the search
        getresult = ImageNeo.nodes.get_or_none(hash=i)  # fetching each corresponding node
        if getresult:  # if it exists
            results["results"].append((getresult, getresult.tag.all()))  # append the node and its tags
    return results

## Searching by text
#
#  More details.
def query_search_page_resources(request):
    logging.info("[Searching]: [INFO] Started Searching.")
    query = SearchForm()  # cleaning this form
    image = SearchForImageForm()  # fetching the images form
    query_text = request.GET.get("query")  # fetching the inputted query
    query_array = process_query(query_text)  # processing query with nlp
    query_original = process_text(query_text)
    tag = "#" + " #".join(query_original)  # arranging tags with '#' before
    results_ = get_image_results(query_array, 1)
    logging.info("[Searching]: [INFO] Finished Searching.")
    if len(results_.keys()) != 0:
        key = list(results_.keys())[0]
    if len(query_array) > 0:
        def sort_by_score(elem):
            image = elem[0]
            tags = elem[1]
            score = 0
            for t in tags:  # t -> Tag (NeoNode)
                for q in query_array:
                    if q in t.name:
                        score += image.tag.relationship(t).score
                        break
            return - (score / len(query_array))

        results_[key].sort(key=sort_by_score)
    results = {}
    results[tag] = [(a, b, a.getPersonsName()) for a, b in results_[key]]
    return image, query, results

content_type_json = 'text/json'
## Image results showing slowly (lazy loading)
# this function loads images depending on the page it receives
#  More details.
def lazy_loading(request, page, name):
    query_array = name.split(" ")
    logging.info("[Searching]: [INFO] Started Searching.")
    results = get_image_results(query_array, page)
    logging.info("[Searching]: [INFO] Finished Searching.")
    if len(results.keys()) > 0:
        key = list(results.keys())[0]
        def sort_by_score(elem):
            image = elem[0]
            tags = elem[1]
            score = 0
            for t in tags:  # t -> Tag (NeoNode)
                for q in query_array:
                    if q in t.name:
                        score += image.tag.relationship(t).score
                        break
            return - (score / max(1, len(query_array)))

        results[key].sort(key=sort_by_score)
        returning = {}

        create_return_lazy(key, results, returning)

        import json
        return HttpResponse(json.dumps(returning), content_type=content_type_json)

## This will transform the results into a dictionary
# So that it can transform into a json type
#  More details.
def create_return_lazy(key, results, returning):
    for result in results[key]:
        image_neo = result[0]
        if (result[0].hash not in returning):
            returning[result[0].hash] = {}
        returning[result[0].hash]["folder_uri"] = image_neo.folder_uri
        returning[result[0].hash]["name"] = image_neo.name
        returning[result[0].hash]["width"] = image_neo.width
        returning[result[0].hash]["height"] = image_neo.height
        returning[result[0].hash]["creation_date"] = image_neo.creation_date
        tag_list = []
        for tag in result[1]:
            tag_entity = tag
            tag_list += [tag_entity.name]
        returning[result[0].hash]["tags"] = tag_list
        returning[result[0].hash]["persons"] = result[0].getPersonsName()

## Reloads filters
#
#  More details.
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

        set_from_insertion_date(form, time_format_string)

        set_to_insertion_date(form, time_format_string)

    searchFilterOptions['taken_date_activate'] = form['taken_date_activate']
    if searchFilterOptions['taken_date_activate']: # update dates
        set_from_taken_date(form, time_format_string)

        set_to_taken_date(form, time_format_string)

    # -- confiance object extraction --
    max_obj_extr = form['objects_range_max']
    min_obj_extr = form['objects_range_min']

    max_obj_extr, min_obj_extr = set_object_extr_limits(max_obj_extr, min_obj_extr)

    searchFilterOptions['objects_range_max'] = int(max_obj_extr)
    searchFilterOptions['objects_range_min'] = int(min_obj_extr)
    # -- end confiance object extraction --
    # -- confiance face rec --
    max_face = form['people_range_max']
    min_face = form['people_range_min']

    max_face, min_face = set_face_rec_limits(max_face, min_face, min_obj_extr)

    searchFilterOptions['people_range_max'] = int(max_face)
    searchFilterOptions['people_range_min'] = int(min_face)
    # -- end confiance face rec --


    # -- confiance breeds --
    max_breeds = form['breeds_range_max']
    min_breeds = form['breeds_range_min']

    max_breeds, min_breeds = set_breeds_limits(max_breeds, min_breeds)

    searchFilterOptions['breeds_range_max'] = int(max_breeds)
    searchFilterOptions['breeds_range_min'] = int(min_breeds)
    # -- end confiance breeds --


    # -- confiance places --
    max_places = form['places_range_max']
    min_places = form['places_range_min']

    max_places, min_places = set_places_limits(max_places, min_places)

    searchFilterOptions['places_range_max'] = int(max_places)
    searchFilterOptions['places_range_min'] = int(min_places)
    # -- end confiance places --

    return redirect(form['current_url'])

## Sets filter places limits
#
#  More details.
def set_places_limits(max_places, min_places):
    if min_places < placesThreshold * 100:
        min_places = placesThreshold * 100
    elif min_places > 100:
        min_places = 100
    if max_places < min_places:
        max_places = min_places
    elif max_places > 100:
        max_places = 100
    return max_places, min_places

## Sets filter breeds limits
#
#  More details.
def set_breeds_limits(max_breeds, min_breeds):
    if min_breeds < breedsThreshold * 100:
        min_breeds = breedsThreshold * 100
    elif min_breeds > 100:
        min_breeds = 100
    if max_breeds < min_breeds:
        max_breeds = min_breeds
    elif max_breeds > 100:
        max_breeds = 100
    return max_breeds, min_breeds

## Sets filter faces limits
#
#  More details.
def set_face_rec_limits(max_face, min_face, min_obj_extr):
    if min_face < faceRecThreshold * 100:
        min_face = faceRecThreshold * 100
    elif min_face > 100:
        min_face = 100
    if max_face < min_obj_extr:
        max_face = min_obj_extr
    elif max_face > 100:
        max_face = 100
    return max_face, min_face

## Sets filter objects limits
#
#  More details.
def set_object_extr_limits(max_obj_extr, min_obj_extr):
    if min_obj_extr < objectExtractionThreshold * 100:
        min_obj_extr = objectExtractionThreshold * 100
    elif min_obj_extr > 100:
        min_obj_extr = 100
    if max_obj_extr < min_obj_extr:
        max_obj_extr = min_obj_extr
    elif max_obj_extr > 100:
        max_obj_extr = 100
    return max_obj_extr, min_obj_extr

## Sets filter top taken date
#
#  More details.
def set_to_taken_date(form, time_format_string):
    try:
        timeHelper['taken_date_to'] = datetime.datetime.strptime(form['taken_date_to'], time_format_string)
        searchFilterOptions['taken_date_to'] = form['taken_date_to']
    except ValueError:  # invalid format
        searchFilterOptions['taken_date_to'] = None
        timeHelper['taken_date_to'] = None

## Sets filter bottom taken date
#
#  More details.
def set_from_taken_date(form, time_format_string):
    try:
        timeHelper['taken_date_from'] = datetime.datetime.strptime(form['taken_date_from'], time_format_string)
        searchFilterOptions['taken_date_from'] = form['taken_date_from']
    except ValueError:  # invalid format
        searchFilterOptions['taken_date_from'] = None
        timeHelper['taken_date_from'] = None

## Sets filter top insertion date
#
#  More details.
def set_to_insertion_date(form, time_format_string):
    try:
        timeHelper['insertion_date_to'] = datetime.datetime.strptime(form['insertion_date_to'], time_format_string)
        searchFilterOptions['insertion_date_to'] = form['insertion_date_to']
    except ValueError:  # invalid format
        searchFilterOptions['insertion_date_to'] = None
        timeHelper['insertion_date_to'] = None

## Sets filter bottom insertion date
#
#  More details.
def set_from_insertion_date(form, time_format_string):
    try:
        timeHelper['insertion_date_from'] = datetime.datetime.strptime(form['insertion_date_from'], time_format_string)
        searchFilterOptions['insertion_date_from'] = form['insertion_date_from']
    except ValueError:  # invalid format
        searchFilterOptions['insertion_date_from'] = None
        timeHelper['insertion_date_from'] = None


isBeforeThan = lambda datee, filter_ : (datee.replace(tzinfo=None) - filter_.replace(tzinfo=None)).days < 0
isLaterThan = lambda datee, filter_ : (datee.replace(tzinfo=None) - filter_.replace(tzinfo=None)).days > 0
## Gets image results in a query
#
#  More details.
def get_image_results(query_array,page):
    tag = "#" + " #".join(query_array)  # arranging tags with '#' before

    result_hashs = [x.meta.id for x in search(query_array,page)]

    #print('len result_hashs : ' , len(result_hashs))
    results = {tag: []}  # blank results dictionary
    for hash in result_hashs:  # iterating through the result's hashes
        remove = set()
        img = ImageNeo.nodes.get_or_none(hash=hash)  # fetching the reuslts nodes from DB
        skip = check_if_image_in_filter_sizes(img)
        if skip:
            continue


        # ---- dates -----
        skip = check_if_image_in_filter_dates(img)
        if skip:
            continue

        #       ---- people ---

        remove_image_not_in_filter_persons(img, query_array, remove)

        # -- manual --
        remove_image_not_in_filter_manual(img, query_array, remove)

        # -- object --
        remove_image_not_in_filter_objects(img, query_array, remove)

        # -- ocr --
        remove_image_not_in_filter_ocr(img, query_array, remove)

        # -- places --
        remove_image_not_in_filter_places(img, query_array, remove)

        # -- breeds --
        remove_image_not_in_filter_breeds(img, query_array, remove)

        # locations
        locations = [t for t in img.location ]
        regions = [r for l in locations for c in l.city for r in c.region]
        countries = [country for r in regions for country in r.country]
        tags = locations + regions + countries
        tags = [t.name.lower() for t in tags]

        dentro = any([q in t for q in query_array for t in tags])
        if dentro:
            remove.add(False)

        remove_unwanted_images_from_search_results(img, remove, results, tag)

    return results

## Removes unwanted images from results
#
#  More details.
def remove_unwanted_images_from_search_results(img, remove, results, tag):
    if not all(remove):
        img.features = None
        all_img_tags = img.tag.all()
        set_all_img_tags = []
        for tag_object in all_img_tags:
            if tag_object not in set_all_img_tags:
                set_all_img_tags += [tag_object]
        results[tag].append((img, set_all_img_tags))  # insert tags in the dictionary

## Removes images not in filter breeds
#
#  More details.
def remove_image_not_in_filter_breeds(img, query_array, remove):
    tags = [t.name.lower() for t in img.tag.match(originalTagSource='breeds')]
    dentro = any([q in t for q in query_array for t in tags])
    if dentro:
        # print('dentro breeds')
        if not searchFilterOptions['breeds']:
            remove.add(True)
        else:
            tags = [t for t in img.tag.match(originalTagSource='breeds')]
            relationships = [img.tag.all_relationships(t) for t in tags if
                             not set(t.name.lower().split(' ')).isdisjoint(query_array)]
            relationships = [rel for r in relationships for rel in r]
            # if len(relationships) > 0:
            minn = searchFilterOptions['breeds_range_min']
            maxx = searchFilterOptions['breeds_range_max']
            outside_limits = all([rel.score * 100 < minn or rel.score * 100 > maxx for rel in relationships])
            # print('breeds', [rel.score for rel in relationships])
            remove.add(outside_limits)

## Removes images not in filter places
#
#  More details.
def remove_image_not_in_filter_places(img, query_array, remove):
    tags = [t.name.lower() for t in img.tag.match(originalTagSource='places')]
    dentro = any([q in t for q in query_array for t in tags])
    if dentro:
        if not searchFilterOptions['places']:
            remove.add(True)
        else:
            tags = [t for t in img.tag.match(originalTagSource='places')]
            relationships = [img.tag.all_relationships(t) for t in tags if
                             not set(t.name.lower().split(' ')).isdisjoint(query_array)]
            relationships = [rel for r in relationships for rel in r]
            # if len(relationships) > 0:
            minn = searchFilterOptions['places_range_min']
            maxx = searchFilterOptions['places_range_max']
            outside_limits = all([rel.score * 100 < minn or rel.score * 100 > maxx for rel in relationships])
            remove.add(outside_limits)

## Removes images not in filter ocr
#
#  More details.
def remove_image_not_in_filter_ocr(img, query_array, remove):
    tags = [t.name.lower() for t in img.tag.match(originalTagSource='ocr')]
    dentro = any([q in t for q in query_array for t in tags])
    if dentro:
        remove.add(not searchFilterOptions['text'])

## Removes images not in filter objects
#
#  More details.
def remove_image_not_in_filter_objects(img, query_array, remove):
    tags = [t.name.lower() for t in img.tag.match(originalTagSource='object')]
    dentro = any([q in t for q in query_array for t in tags])
    if dentro:
        if not searchFilterOptions['automatic']:
            remove.add(True)
        else:
            tags = [t for t in img.tag.match(originalTagSource='object')]
            relationships = [img.tag.all_relationships(t) for t in tags if
                             not set(t.name.lower().split(' ')).isdisjoint(query_array)]
            relationships = [rel for r in relationships for rel in r]
            # if len(relationships) > 0:
            minn = searchFilterOptions['objects_range_min']
            maxx = searchFilterOptions['objects_range_max']
            outside_limits = all([rel.score * 100 < minn or rel.score * 100 > maxx for rel in relationships])
            # print([rel.score for rel in relationships])
            remove.add(outside_limits)  # adiciona Falso se n houver nenhum

## Removes images not in filter manual
#
#  More details.
def remove_image_not_in_filter_manual(img, query_array, remove):
    tags = [t.name.lower() for t in img.tag.match(originalTagSource='manual')]
    dentro = any([q in t for q in query_array for t in tags])
    if dentro:
        remove.add(not searchFilterOptions['manual'])

## Removes images not in filter persons
#
#  More details.
def remove_image_not_in_filter_persons(img, query_array, remove):
    people = img.person.all()
    # verifica se a query ta dentro do nome
    dentro = any([q in p.name.lower() for q in query_array for p in people])
    if dentro:
        if not searchFilterOptions['people']:
            remove.add(True)
        else:
            people = img.person.all()
            relationships = [img.person.all_relationships(t) for t in people if
                             not set(t.name.lower().split(' ')).isdisjoint(query_array)]
            relationships = [rel for r in relationships for rel in r]
            # print('len rels', len(relationships))
            # if len(relationships) > 0:
            minn = searchFilterOptions['people_range_min']
            maxx = searchFilterOptions['people_range_max']
            outside_limits = all([rel.confiance * 100 < minn or rel.confiance * 100 > maxx for rel in relationships])
            # print([rel.confiance for rel in relationships])
            remove.add(outside_limits)

## Removes images not in filter dates
#
#  More details.
def check_if_image_in_filter_dates(img):
    returns = False
    if searchFilterOptions['insertion_date_activate']:
        returns |= check_if_image_in_filter_date_inserted(img)
    if searchFilterOptions['taken_date_activate']:
        returns |= check_if_image_in_filter_date_taken(img)
    return returns

## Removes images not in filter insertion date
#
#  More details.
def check_if_image_in_filter_date_inserted(img):
    fromm = timeHelper['insertion_date_from']
    if fromm is not None and isBeforeThan(img.insertion_date, fromm):
        return True  # is before the limit, not shown
    too = timeHelper['insertion_date_to']
    if too is not None and isLaterThan(img.insertion_date, too):
        return True
    return False

## Removes images not in filter taken date
#
#  More details.
def check_if_image_in_filter_date_taken(img):
    if img.creation_date is None:
        return True
    try:
        d = datetime.datetime.strptime(img.creation_date, '%Y:%m:%d %H:%M:%S')
    except ValueError:  # invalid format
        return True
    fromm = timeHelper['taken_date_from']
    if fromm is not None and isBeforeThan(d, fromm):
        return True  # is before the limit, not shown
    too = timeHelper['taken_date_to']
    if too is not None and isLaterThan(d, too):
        return True
    return False

## Removes images not in the correct filter sizes
#
#  More details.
def check_if_image_in_filter_sizes(img):
    if img is None:  # if there is no image with this hash in DB
        return True  # ignore, advance
    if not searchFilterOptions['size_small'] and is_small(img.height, img.width):
        return True
    if not searchFilterOptions['size_medium'] and is_medium(img.height, img.width):
        return True
    if not searchFilterOptions['size_large'] and is_large(img.height, img.width):
        return True
    return False

## search images of a folder
#
#  More details.
def search_folder(request, name, page):
    if page > 1:
        return search_folder_json(request, name, page)

    results = {}
    results['results'] = get_all_images_of_folder(name, 1)

    opts = searchFilterOptions
    opts['current_url'] = request.get_full_path()
    filters = FilterSearchForm(initial=opts)
    query = SearchForm()  # query form stays the same
    image = SearchForImageForm()  # fetching image form response
    
    return render(request, index_string,
                  {'filters_form': filters, 'form': query, 'image_form': image, 'results': results, 'error': False})

## search images of a folder for lazy loading transforms into a json
#
#  More details.
def search_folder_json(request, name, page):
    results = {}
    results['results'] = get_all_images_of_folder(name, page)
    returning = {}
    for result in results['results']:
        image_neo = result[0]
        if (image_neo.hash not in returning):
            returning[image_neo.hash] = {}

        returning[image_neo.hash]["folder_uri"] = image_neo.folder_uri
        returning[image_neo.hash]["name"] = image_neo.name
        returning[image_neo.hash]["width"] = image_neo.width
        returning[image_neo.hash]["height"] = image_neo.height
        returning[image_neo.hash]["creation_date"] = image_neo.creation_date
        tag_list = []
        for tag in result[1]:
            tag_list += [tag.name]
        returning[image_neo.hash]["tags"] = tag_list
        returning[image_neo.hash]["persons"] = result[2]
    import json
    return HttpResponse(json.dumps(returning), content_type=content_type_json)



to_folders = '/folders'
## Deletes a folder and its respective images
#
#  More details.
def delete(request, path):
    do(delete_folder, path)
    response = redirect(to_folders)
    return response
## Gets the folder managing page and it is where we upload an image
#
#  More details.
def managefolders(request):
    if 'path' in request.GET:
        upload_images(request.GET.get('path'))
        '''
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.getAllUris()
        '''
        response = redirect(to_folders)
        return response
    else:
        form = SearchForm()
        image = SearchForImageForm()
        pathf = EditFoldersForm()
        folders = fs.get_all_uris()
        folders_with_url = [] 
        for folder in folders:
            folders_with_url += [(folder, folder.replace("/","\\"))]
        return render(request, 'managefolders.html',
                      {'form': form, 'image_form': image, 'folders': folders_with_url, 'path_form': pathf})

people_url_string = '/people'
## Managing faces page where we submit and check each face
#
#  More details.
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
## Elastic search search access
#
#  More details.
def search(tags,page):
    image_in_page = 20
    q = Q('bool', should=[Q('term', tags=tag) for tag in tags], minimum_should_match=1)
    s = Search(using=es, index='image').query(q).extra(from_=(page-1)*image_in_page, size=page*image_in_page)
    return s.execute()
## When an image is already processed
#
#  More details.
def already_processed(img_path):
    image = cv2.imread(img_path)
    image_hash = dhash(image)
    existed = ImageNeo.nodes.get_or_none(hash=image_hash)

    return True if existed else False
## Upload of an image
#
#  More details.
def upload(request):
    data = json.loads(request.body)
    upload_images(data["path"])
    return redirect(to_folders)
## Search in ElasticSearch by tag
#
#  More details.
def searchtag(request):
    get = [request.GET.get('tag')]
    q = Q('bool', should=[Q('term', tags=tag) for tag in get], minimum_should_match=1)
    s = Search(using=es, index='image').query(q)
    s.execute()
    return render(request, 'index.html')
## Updating all folders
#
#  More details.
def update_folders(request):
    folders = fs.get_all_uris()
    for folder in folders:
        upload_images(folder)
    return HttpResponseRedirect(reverse('managefolders'))
## Updating faces
#
#  More details.
def update_faces(request):
    if request.method != 'POST':
        redirect(people_url_string)

    form = PersonsForm(request.POST)
    form.is_valid()
        #print('invalid form!!!')

    #print(form.cleaned_data)
    data = form.cleaned_data

    imgs = int(len(form.cleaned_data) / 5)

    faceRecLock.acquire()
    try:
        for i in range(imgs):
            # if not data['person_verified_%s' % str(i)]:
            #    continue
            thumbname = data['person_image_%s' % str(i)]
            new_personname = data['person_name_%s' % str(i)]

            old_personname = data['person_before_%s' % str(i)]
            verified = True
            if not data['person_verified_%s' % str(i)]:
                # continue
                new_personname = old_personname
                verified = False

            # if old_personname != new_personname:
            image_hash = data['person_image_id_%s' % str(i)]

            frr.change_relationship(image_hash, new_personname, old_personname, thumbnail=thumbname, approved=verified)
            if old_personname != new_personname:
                frr.change_name_tag_es(image_hash, new_personname, old_personname)

        frr.update_data()

        if 'reload' in request.POST:
            #print('reload was called')
            frr.reload()
    finally:
        faceRecLock.release()


    return redirect(people_url_string)
## Dashboard page request setup
#
#  More details.
def dashboard(request):
    form = SearchForm()
    image = SearchForImageForm()
    person_number = len(Person.nodes)

    location_number = len(Location.nodes)

    results = {}

    count_tags = {}
    for tag_name, count in Tag().getTop10Tags():
        count_tags[tag_name] = count

    ## original tag source statistics
    count_original_tag_source = {}
    all_tag_labels = {"ocr": "text", "manual": "manual", "object": "objects", "places": "places",
                    "location": "locations", "folder": "folders", "breeds": "breeds", "person": "people"}

    for source_name, tags_count in Tag().tagSourceStatistics():
        count_original_tag_source[source_name] = tags_count

    count_original_tag_source["person"] = Person().countPerson()[0]

    count_original_tag_source["folder"] = Folder().countTerminatedFolders()[0]

    count_original_tag_source["location"] = Location().countLocations()[0]

    for tag_key in all_tag_labels.keys():
        if tag_key not in count_original_tag_source.keys():
            count_original_tag_source[tag_key] = 0
        
    count_original_tag_source = dict(sorted(count_original_tag_source.items(), key=lambda item: item[1]))
    #print(count_original_tag_source)
    return render(request, 'dashboard.html',
                  {'form': form, 'image_form': image, 'results': results, 'counts': count_tags,
                   'countTagSource': count_original_tag_source, 'numbers': {'person': person_number, 'location': location_number}})
## Calender gallery page setup
#
#  More details.
def calendar_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    dates_insertion = {}
    dates_creation = {}
    previous_images = []
    img_list = ImageNeo.nodes.all()

    for img in img_list:
        if img not in previous_images:
            insertion_date = str(img.insertion_date)
            creation_date = str(img.creation_date)
            insertion_date = insertion_date.split(" ")[0]
            creation_date = creation_date.split(" ")[0]

            create_or_add_to_insertion_and_creation_date(creation_date, dates_creation, dates_insertion, insertion_date)

            previous_images += [img]

        else:
            continue

    dates_insertion = dict(sorted(dates_insertion.items(), key=lambda item: item[0]))
    dates_insertion = json.dumps(dates_insertion)
    dates_creation = dict(sorted(dates_creation.items(), key=lambda item: item[0]))
    dates_creation = json.dumps(dates_creation)
    return render(request, 'gallery.html',
                  {'form': form, 'image_form': image, 'datesInsertion': dates_insertion, 'datesCreation': dates_creation})

## creating or adding to insertion and creation date
#
#  More details.
def create_or_add_to_insertion_and_creation_date(creation_date, dates_creation, dates_insertion, insertion_date):
    if insertion_date not in dates_insertion:
        dates_insertion[insertion_date] = 1
    else:
        dates_insertion[insertion_date] += 1
    if creation_date != "None":
        if creation_date not in dates_creation:
            dates_creation[creation_date] = 1
        else:
            dates_creation[creation_date] += 1

## Objects gallery page setup
#
#  More details.
def objects_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_object_tags = {}
    for letter,tag_name in Tag().getTags("object"):
        if letter in all_object_tags:
            all_object_tags[letter] += [tag_name]
        else:
            all_object_tags[letter] = [tag_name]

    return render(request, 'objectsGallery.html',
                  {'form': form, 'image_form': image, 'objectTags': all_object_tags})
## People gallery page setup
#
#  More details.
def people_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_names = Person().getVerified()

    all_names = sorted(list(set(all_names)))

    #print(all_names)

    all_names_dict = {}

    for name in all_names:
        first_letter = name[0]
        if first_letter not in all_names_dict.keys():
            all_names_dict[first_letter] = [name]
        else:
            all_names_dict[first_letter] += [name]
    #print(all_names_dict)
    return render(request, 'peopleGallery.html',
                  {'form': form, 'image_form': image, 'people': all_names_dict})
## Scenes or places gallery page setup
#
#  More details.
def scenes_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_place_tags = {}
    for letter,tag_name in Tag().getTags("places"):
        if letter in all_place_tags:
            all_place_tags[letter] += [tag_name]
        else:
            all_place_tags[letter] = [tag_name]  

    return render(request, 'placesGallery.html',
                  {'form': form, 'image_form': image, 'placesTags': all_place_tags})
## Text gallery page setup
#
#  More details.
def text_gallery(request):
    form = SearchForm()
    image = SearchForImageForm()
    all_text_tags = {}
    for letter,tag_name in Tag().getTags("ocr"):
        if letter in all_text_tags:
            all_text_tags[letter] += [tag_name]
        else:
            all_text_tags[letter] = [tag_name]
            
    return render(request, 'textGallery.html',
                  {'form': form, 'image_form': image, 'textTags': all_text_tags})
## Exporting to zip
#
#  More details.
def export_to_zip(request, ids):
    ids = ids[1:]
    if ids.strip() == '':
        return HttpResponse(content_type=content_type_json)

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
## Exporting to excel
#
#  More details.
def export_to_excel(request, ids):
    ids = ids[1:]
    if ids.strip() == '':
        return HttpResponse(content_type=content_type_json)

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

        iterate_through_all_neo_nodes(img, locations)

        csv_file.writerow([uri, creation_time, insertion_date, img_format, width,
                           height, tags, persons, locations])

    return response

## Iterates through neo4j nodes to get locations, their cities, the cities region, and the regions country
#
#  More details.
def iterate_through_all_neo_nodes(img, locations):
    for l in img.location:
        locations.append(l.name)
        for city in l.city:
            locations.append(city.name)
            for region in city.region:
                locations.append(region.name)
                for country in region.country:
                    locations.append(country.name)
