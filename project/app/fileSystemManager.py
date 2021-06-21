## @package app
#  This is the local file system manager so that we can easily
# check folders and get paths easily
#  More details.
import logging
import os
import re
import sys

from app.models import ImageES,Folder
from scripts.esScript import es
from app.utils import get_random_number, ImageFeature, processingLock
## Class node that is the folder
# Contains:
#   folder name
#   folder children (a dictionary of nodes)
#   folder parent (a node or None if it doesn't have a parent)
#   folder id
#   deleting if it is being deleted or not (Stars with False)
#   terminated if the current node is the last one of a path then it is terminated
# example: for uri C:\User\abcd\ef\, node 'ef' is terminated
#  More details.
class Node:
    def __init__(self, name: str, id: int, terminated=False):
        self.name = name  # folder name
        self.children = {}  # key: folder name, value: node
        self.parent = None
        self.id = id

        self.deleting = False

        # if current node is the last one of an uri, it is terminated
        # ex: for uri C:\User\abcd\ef\, node 'ef' is terminated
        self.terminated = terminated


    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    ## Deletes a node
    #       pop
    #  More details.
    def delete_node(self, node):
        if node.name in self.children:
            self.children.pop(node.name)
## File system manager class
# This is where the file system manager tree is created
#  More details.
class SimpleFileSystemManager:
    ## Starting with an empty dictionary
    # with key: folder name and value node
    #  More details.
    def __init__(self):
        self.trees = {}  # key: folder name, value: node.

    ## Function checks if an uri exists in the file system
    # @param uri: String
    #  More details.
    def exist(self, uri: str):
        folders, root = self.__split_uri_and_get_root__(uri)

        if root in self.trees:
            node = self.trees[root]
            for i in range(1, len(folders)):
                folder = folders[i].strip()
                if folder == "":
                    continue

                if folder in node.children:
                    node = node.children[folder]
                else:
                    return False
        else:
            return False

        return node.terminated ^ node.deleting

    ## Adds a full path to the file system
    # @param uri: string (the path)
    # @param ids: list(integers)
    #  More details.
    def add_full_path_uri(self, uri: str, ids: list):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        if len(folders) != len(ids): return

        if self.exist(uri): return

        root = folders[0]

        if root in self.trees:
            node = self.trees[root]
        else:
            self.trees[root] = node = Node(root, ids[0])

        for i in range(1, len(folders)):
            folder = folders[i]

            if folder in node.children:
                node = node.children[folder]
            else:
                new_node = Node(folder, ids[i])
                new_node.parent = node
                node.children[folder] = node = new_node

        node.terminated = True

    ## Add a new folder under the given uri
    # given uri must exist in fileSystemManager
    #  More details.
    def expand_uri(self, uri, folder, id):
        folders, root = self.__split_uri_and_get_root__(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                f = folders[i]
                if f in node.children:
                    node = node.children[f]

            new_node = Node(folder, id)
            new_node.terminated = True
            node.children[folder] = new_node

    ## gets the last node of an uri
    # @param uri String (path of a directory)
    #  More details.
    def get_last_node(self, uri):
        folders, root = self.__split_uri_and_get_root__(uri)

        if root in self.trees:
            node = self.trees[root]

            for i in range(1, len(folders)):
                folder = folders[i]
                if folder in node.children:
                    node = node.children[folder]
                else:
                    return None

            return node

    ## Creates uri in neo4j
    # @param uri: String (path of a directory)
    #  More details.
    def create_uri_in_neo4j(self, uri):
        folders, root = self.__split_uri_and_get_root__(uri)

        logging.info("[SERVER-TO-NEO]: [INFO] Creating uri: " + str(uri) + " Folders found: " + str(folders))

        if root in self.trees:
            node = self.trees[root]
            if len(folders) == 1:
                node.terminated = True
                return node
        else:
            saved_node = Folder(id_=get_random_number(), name=root, root=True,
                                terminated=True if len(folders) == 1 else False).save()
            self.trees[root] = node = Node(root, saved_node.id_)

        node = self.create_uri_in_neo4j_for_folders(folders, node)
        return node

    ## We go through each node from the folders and
    # save it in neo4j as a folder
    #  More details.
    def create_uri_in_neo4j_for_folders(self, folders, node):
        for i in range(1, len(folders)):
            folder = folders[i]
            if folder in node.children:
                node = node.children[folder]
                if i == len(folders) - 1:
                    node.terminated = True
            else:
                saved_node = Folder(id_=get_random_number(), name=folder,
                                    terminated=True if i == len(folders) - 1 else False).save()

                parent = Folder.nodes.get(id_=node.id)
                saved_node.parent.connect(parent)

                new_node = Node(folder, saved_node.id_, saved_node.terminated)
                new_node.parent = node
                node.children[folder] = node = new_node
        return node

    ## split uri path and get the root of that path
    # @param uri: String (directory path)
    # @rtype tuple of (array,node)
    # @return Returns a tuple of the folders as an array and the root node
    #  More details.
    def __split_uri_and_get_root__(self, uri):
        folders = re.split("[\\\/]+", uri)
        if folders[len(folders) - 1].strip() == "":
            folders = folders[:-1]

        root = folders[0]
        return folders, root

    ## builds a full path from an array of paths
    # @param paths: Array of strings
    #  More details.
    def __buil_full_path__(self, paths):
        path = ""
        for p in paths:
            path = os.path.join(path, p)
        return path

    ## deletes a folder from the file system
    #   @param uri:  string (path of the folder we want to delete)
    #   @param frr: face recognition class
    #  More details.
    def delete_folder_from_fs(self, uri, frr):
        try:
            if self.exist(uri):
                folders_to_be_deleted, node = self.get_folders_to_be_deleted_from_uri(uri)

                deleted_images = self.pop_folders_from_to_be_deleted(folders_to_be_deleted, frr)

                # if parent folders have no children folders and no images, delete it
                node = self.check_for_childrens_and_delete_them(node)

                if node.name in self.trees and len(node.children) == 0:
                    self.trees.pop(node.name)

                return deleted_images
        except Exception as e:
            logging.info("[Deleting]: [ERROR] Delete error " + str(e))

    ## POPS
    # folder
    #  More details.
    def pop_folders_from_to_be_deleted(self, folders_to_be_deleted, frr):
        deleted_images = []
        while folders_to_be_deleted != []:
            f = folders_to_be_deleted.pop()
            if not f:
                continue

            images = f.getImages()

            if images is not None:
                for image in images:
                    try:
                        frr.remove_image(image.hash)
                    except Exception as e:
                        logging.info(
                            "[Deleting]: [ERROR] Couldn't remove person thumbnail and/or person entity because: " + str(
                                e))
                    self.delete_images(deleted_images, f, image)

            children_folders = f.getChildren()
            if children_folders:
                folders_to_be_deleted.extend(list(children_folders))
            f.delete()
        return deleted_images

    ## Get folders that are going to be deleted form the uri
    #   @param uri: String (path of the folder that is being deleted)
    #  More details.
    def get_folders_to_be_deleted_from_uri(self, uri):
        node = self.get_last_node(uri)
        if node and node.parent:
            node.parent.delete_node(node)
        node.deleting = True
        foldersto_be_deleted = [Folder.nodes.get_or_none(id_=node.id)]
        return foldersto_be_deleted, node

    ## Deletes images
    #  More details.
    def delete_images(self, deleted_images, f, image):
        if len(image.folder) > 1:  # if image is in different folders
            current_image_uri, root = self.__split_uri_and_get_root__(image.folder_uri)
            current_image_uri = self.__buil_full_path__(current_image_uri)
            if current_image_uri == self.__full_path_for_folder_node__(f):
                for folder in image.folder:
                    if folder.id != f.id and not folder.isChildOf(f.id_):
                        image.folder_uri = self.__full_path_for_folder_node__(folder)
                        image.save()
                        es_image = ImageES.get(using=es, index='image', id=image.hash)
                        es_image.uri = image.folder_uri
                        es_image.save(using=es)
                        break
        else:
            self.delete_connected_tags_and_persons(image)
            self.delete_locations(image)
            image.delete()

            try:
                thumbnail = os.path.join("app", "static", "thumbnails", str(image.hash)) + ".jpg"
                os.remove(thumbnail)

                es_image = ImageES.get(using=es, index='image', id=image.hash)
                es_image.delete(using=es)
                deleted_images.append(ImageFeature(hash=image.hash))
            except Exception as e:
                logging.info("[Deleting]: [ERROR] Image missing: " + str(e))

    ## Check if a node has children and deltes them
    #   @param node: node class
    #  More details.
    def check_for_childrens_and_delete_them(self, node):
        while node.parent:
            parent_folder = Folder.nodes.get_or_none(id_=node.parent.id)
            if not parent_folder:
                node.parent.delete_node(node)
                node = node.parent
                continue
            curr_node = node
            node = node.parent
            children = parent_folder.getChildren()
            if len(children) == 0 and not parent_folder.terminated:
                parent_folder.delete()
                if curr_node.name in node.children:
                    node.children.pop(curr_node.name)
            else:
                break
        return node

    ## gets full path from a folder node
    #  More details.
    def __full_path_for_folder_node__(self, f):
        paths = f.getFullPath()
        paths.reverse()
        paths.append(f.name)
        return self.__buil_full_path__(paths)

    ## Deletes connected tags and persons of an image
    #   @param image: ImageNeo class
    #  More details.
    def delete_connected_tags_and_persons(self, image):
        if len(image.tag) != 0:
            for t in image.tag:
                t.image.disconnect(image)
                if len(t.image) == 0:
                    t.delete()

        if len(image.person) != 0:
            for p in image.person:
                p.image.disconnect(image)
                if len(p.image) == 0:
                    p.delete()

    ## Deletes connected locations of an image
    #   @param image: ImageNeo class
    #  More details.
    def delete_locations(self, image):
        if len(image.location) != 0:
            for l in image.location:
                l.image.disconnect(image)
                if len(l.image) == 0:
                    self.delete_cities(l)
                    l.delete()

    ## Deletes connected cities
    #   @param l: Location class
    #  More details.
    def delete_cities(self, l):
        for city in l.city:
            city.location.disconnect(l)
            if len(city.location) == 0:
                self.delete_regions(city)
                city.delete()

    ## Deletes connected regions
    #   @param city: City class
    #  More details.
    def delete_regions(self, city):
        for region in city.region:
            region.city.disconnect(city)
            if len(region.city) == 0:
                self.delete_countries(region)
                region.delete()

    ## Deletes connected countries
    #   @param region: Region class
    #  More details.
    def delete_countries(self, region):
        for country in region.country:
            country.region.disconnect(region)
            if len(country.region) == 0:
                country.delete()

    ## Gets all paths from the file system
    #  More details.
    def get_all_uris(self):
        uris = []

        def build_uri(current, uri):
            for folder in current.children:
                path = os.path.join(uri, folder)
                next_node = current.children[folder]
                if next_node.terminated:
                    uris.append(path)
                build_uri(next_node, path)

        for node in self.trees.keys():
            build_uri(self.trees[node], os.path.normpath(node + "/"))

        return uris
